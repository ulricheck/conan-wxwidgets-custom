from conans import ConanFile, CMake
import platform
import os
import glob
import posixpath
import string
import re
from collections import namedtuple
import time

class WxWidgetsConan(ConanFile):
    name = "wxWidgets_custom"
    version = "master"
    settings = {
        "os": ["Windows"],
        "compiler": ["Visual Studio"],
        "build_type": ["Debug", "Release"],
        "arch": ["x86", "x86_64"]
    }
    options = {
        "shared": [True, False],
        "unicode": [True, False],
        "monolithic": [True, False],
        "use_gui": [True, False],
        "wxdebug": [True, False]
    }
    default_options = "shared=True", "unicode=True", "monolithic=False", "use_gui=True", "wxdebug=True"
    exports = "wxWidgets/*"

    # If this is changed, remember to update exports as well.
    repo_subdir = "wxWidgets"

    git_branch_format = "custom-{version}"
    git_branch = None
    git_repository_url = "https://github.com/SteffenL/wxWidgets"

    wx_lib_name_version = None
    wx_platform = None
    wx_compiler_prefix = None
    wx_libs_dir = None
    wx_lib_name_formats = [
        "wxbase{version}{unicode}{debug}",
        "wxbase{version}{unicode}{debug}_net",
        "wxbase{version}{unicode}{debug}_xml",
        "wx{platform}{version}{unicode}{debug}_adv",
        "wx{platform}{version}{unicode}{debug}_aui",
        "wx{platform}{version}{unicode}{debug}_core",
        "wx{platform}{version}{unicode}{debug}_gl",
        "wx{platform}{version}{unicode}{debug}_html",
        "wx{platform}{version}{unicode}{debug}_media",
        "wx{platform}{version}{unicode}{debug}_propgrid",
        "wx{platform}{version}{unicode}{debug}_qa",
        "wx{platform}{version}{unicode}{debug}_ribbon",
        "wx{platform}{version}{unicode}{debug}_richtext",
        "wx{platform}{version}{unicode}{debug}_stc",
        "wx{platform}{version}{unicode}{debug}_webview",
        "wx{platform}{version}{unicode}{debug}_xrc",
        "wxexpat{debug}",
        "wxjpeg{debug}",
        "wxpng{debug}",
        "wxregex{unicode}{debug}",
        "wxscintilla{debug}",
        "wxtiff{debug}",
        "wxzlib{debug}"
    ]
    wx_lib_names = []
    wx_unicode_suffix = ""
    wx_debug_suffix = ""
    wx_build_dir = None
    wx_include_dir = None
    wx_compiler_include_dir = None
    wx_platform_include_dir = None
    wx_compiler_defines = []
    wx_runtime_libs_linkage = "dynamic"
    wx_compile_params = []
    wx_version = None

    wx_compiler_prefix_map = {
        "Visual Studio": "vc"
    }
    wx_compiler_include_dir_map = {
        "Visual Studio": "msvc"
    }
    wx_compiler_runtime_map = {
        "Visual Studio": {
            "MDd": "dynamic",
            "MD": "dynamic",
            "MTd": "static",
            "MT": "static"
        }
    }
    wx_platform_map = {
        "Windows": "msw"
    }
    wx_compiler_defines_for_platform_map = {
        "Windows": ["__WXMSW__", "WINVER=0x0500"]
    }
    wx_compiler_defines_for_compiler_map = {
        "Visual Studio": ["_CRT_SECURE_NO_WARNINGS", "UNICODE", "_UNICODE"]
    }
    wx_build_type_map = {
        "Debug": "debug",
        "Release": "release"
    }
    wx_build_command_format = {
        "Visual Studio": "nmake -f makefile.vc {0}"
    }

    def config(self):
        pass

    def source(self):
        git_branch = self.git_branch_format.format(version=self.version)
        git_clone_params = [
            "--depth 1",
            "--branch %s" % git_branch,
            self.git_repository_url,
            self.repo_subdir
        ]

        self.run("git clone %s" % string.join(git_clone_params, " "))

        self.wx_version = self.read_wx_version(os.path.join(self.repo_subdir, "include/wx/version.h"))
        self.wx_lib_name_version = "".join([str(self.wx_version.major), str(self.wx_version.minor)])
        self.wx_lib_names = self.wx_expand_lib_name_vars(self.wx_lib_name_formats)

    def build(self):
        os.chdir(os.path.join(self.repo_subdir, self.wx_build_dir))
        self.run(self.wx_build_command_format[str(self.settings.compiler)].format(self.wx_compile_params))

    def package(self):
        repo_libs_dir = posixpath.join(self.repo_subdir, self.wx_libs_dir)
        #libs_include_dir_name = self.wx_platform + self.wx_unicode_suffix + self.wx_debug_suffix
        self.copy(pattern="*.dll", dst="bin", src=repo_libs_dir)
        self.copy(pattern="*.lib", dst="lib", src=repo_libs_dir)
        self.copy(pattern="*.h", dst=self.wx_libs_dir, src=repo_libs_dir)
        #self.copy(pattern=libs_include_dir_name, dst="lib", src=repo_libs_dir)
        self.copy(pattern="*", dst="include", src=posixpath.join(self.repo_subdir, self.wx_include_dir))

    def package_info(self):
        self.gather_wx_config()

        self.cpp_info.includedirs = [self.wx_include_dir, self.wx_platform_include_dir, self.wx_compiler_include_dir]
        self.cpp_info.libs = self.wx_lib_names
        self.cpp_info.defines = self.wx_compiler_defines

    def config_compiler_defines(self):
        if self.options.wxdebug:
            self.wx_compiler_defines.append("__WXDEBUG__")

        self.wx_compiler_defines.append("wxUSE_GUI=%s" % 1 if self.options.use_gui else 0)

        if self.options.shared:
            if self.settings.os == "Windows":
                self.wx_compiler_defines.append("WXUSINGDLL")

        self.wx_compiler_defines.extend(self.wx_compiler_defines_for_platform_map[str(self.settings.os)])
        self.wx_compiler_defines.extend(self.wx_compiler_defines_for_compiler_map[str(self.settings.compiler)])

    def config_include_dirs(self):
        self.wx_include_dir = "include"
        self.wx_compiler_include_dir = posixpath.join(self.wx_include_dir, self.wx_compiler_include_dir_map[str(self.settings.compiler)])
        self.wx_platform_include_dir = posixpath.join("lib", self.wx_platform + self.wx_unicode_suffix)

    def wx_expand_lib_name_vars(self, name_format_list):
        return [
            name_format.format(
                platform=self.wx_platform,
                version=self.wx_lib_name_version,
                unicode=self.wx_unicode_suffix,
                debug=self.wx_debug_suffix
            ) for name_format in name_format_list
        ]

    def read_wx_version(self, version_header_path):
        with open(version_header_path, "r") as f:
            content = f.read()
            version = Version(
                int(re.search("wxMAJOR_VERSION\s+(\d+)", content).groups()[0]),
                int(re.search("wxMINOR_VERSION\s+(\d+)", content).groups()[0]),
                int(re.search("wxRELEASE_NUMBER\s+(\d+)", content).groups()[0])
            )
            return version

    def gather_wx_config(self):
        self.wx_platform = self.wx_platform_map[str(self.settings.os)]
        self.wx_compiler_prefix = self.wx_compiler_prefix_map[str(self.settings.compiler)]

        if self.settings.compiler.runtime != None:
            runtime_map = self.wx_compiler_runtime_map[str(self.settings.compiler)]
            self.wx_runtime_libs_linkage = runtime_map[str(self.settings.compiler.runtime)] 

        if self.options.unicode:
            self.wx_unicode_suffix = "u"

        if self.settings.build_type == "Debug":
            self.wx_debug_suffix = "d"

        self.wx_libs_dir = posixpath.join("lib/{0}_{1}{2}".format(
            self.wx_compiler_prefix,
            "x64" + "_" if self.settings.arch == "x86_64" else "",
            # TODO: Check this for platforms other than Windows
            "dll" if self.options.shared else "lib"
        ))

        self.config_compiler_defines()
        self.config_include_dirs()

        self.wx_build_dir = posixpath.join("build", self.wx_platform)
        self.wx_compile_params = "RUNTIME_LIBS={runtime_libs} UNICODE={unicode} SHARED={shared} MONOLITHIC={monolithic} TARGET_CPU={target_cpu} BUILD={build}".format(
            runtime_libs=self.wx_runtime_libs_linkage,
            unicode=1 if self.options.unicode else 0,
            shared=1 if self.options.shared else 0,
            monolithic=1 if self.options.monolithic else 0,
            target_cpu="x64" if self.settings.arch == "x86_64" else "x86",
            build=self.wx_build_type_map[str(self.settings.build_type)]
        )

        print("------------------------------------------------------------")
        print("conan settings:")
        print("\n".join(["{0} = {1}".format(k, v) for k, v in self.settings.items()]))
        print("")
        print("conan options:")
        print("\n".join(["{0} = {1}".format(k, v) for k, v in self.options.items()]))
        print("")
        print("wx compile params:")
        print(self.wx_compile_params)
        print("------------------------------------------------------------")

class Version:
    major = None
    minor = None
    release = None

    def __init__(self, major, minor, release):
        self.major = major
        self.minor = minor
        self.release = release 
