#
# Copyright (c) 2016, 2018, Oracle and/or its affiliates.
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are
# permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this list of
# conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice, this list of
# conditions and the following disclaimer in the documentation and/or other materials provided
# with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors may be used to
# endorse or promote products derived from this software without specific prior written
# permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
# GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE.
#
import re
import tempfile

import mx, mx_benchmark, mx_sulong, mx_buildtools
import os
import mx_subst
from os.path import join, exists
from mx_benchmark import VmRegistry, java_vm_registry, Vm, GuestVm, VmBenchmarkSuite


def _benchmarksDirectory():
    return join(os.path.abspath(join(mx.suite('sulong').dir, os.pardir, os.pardir)), 'sulong-benchmarks')

_env_flags = []
if 'CPPFLAGS' in os.environ:
    _env_flags = os.environ['CPPFLAGS'].split(' ')


class SulongBenchmarkRule(mx_benchmark.StdOutRule):
    def __init__(self, replacement):
        super(SulongBenchmarkRule, self).__init__(
            pattern=r'^last 10 iterations (?P<benchmark>[\S]+):(?P<line>([ ,]+(?:\d+(?:\.\d+)?))+)',
            replacement=replacement)

    def parseResults(self, text):
        def _parse_results_gen():
            for d in super(SulongBenchmarkRule, self).parseResults(text):
                line = d.pop('line')
                for value in line.split(','):
                    r = d.copy()
                    r['score'] = value.strip()
                    yield r

        return (x for x in _parse_results_gen())


class SulongBenchmarkSuite(VmBenchmarkSuite):
    def __init__(self, *args, **kwargs):
        super(SulongBenchmarkSuite, self).__init__(*args, **kwargs)
        self.bench_to_exec = {}

    def group(self):
        return 'Graal'

    def subgroup(self):
        return 'sulong'

    def name(self):
        return 'csuite'

    def run(self, benchnames, bmSuiteArgs):
        vm = self.get_vm_registry().get_vm_from_suite_args(bmSuiteArgs)
        assert isinstance(vm, CExecutionEnvironmentMixin)

        # compile benchmarks

        # save current Directory
        currentDir = os.getcwd()
        for bench in benchnames:
            try:
                # benchmark dir
                path = self.workingDirectory(benchnames, bmSuiteArgs)
                # create directory for executable of this vm
                if not os.path.exists(path):
                    os.makedirs(path)
                os.chdir(path)

                native_out = 'bench'
                if os.path.exists(native_out):
                    os.remove(native_out)

                env = os.environ.copy()
                env['VPATH'] = '..'

                env = vm.prepare_env(env)
                cmdline = ['make', '-f', '../Makefile']
                if mx._opts.verbose:
                    # The Makefiles should have logic to disable the @ sign
                    # so that all executed commands are visible.
                    cmdline += ["MX_VERBOSE=y"]
                mx.run(cmdline, env=env)
                opt_out = vm.post_process_executable(native_out)
                self.bench_to_exec[bench] = os.path.abspath(opt_out)
            finally:
                # reset current Directory
                os.chdir(currentDir)

        return super(SulongBenchmarkSuite, self).run(benchnames, bmSuiteArgs)

    def benchmarkList(self, bmSuiteArgs):
        benchDir = _benchmarksDirectory()
        if not exists(benchDir):
            mx.abort('Benchmarks directory {} is missing'.format(benchDir))
        return [f for f in os.listdir(benchDir) if os.path.isdir(join(benchDir, f)) and os.path.isfile(join(join(benchDir, f), 'Makefile'))]

    def failurePatterns(self):
        return [
            re.compile(r'error:'),
            re.compile(r'Exception')
        ]

    def successPatterns(self):
        return [re.compile(r'^(### )?([a-zA-Z0-9\.\-_]+): +([0-9]+(?:\.[0-9]+)?)', re.MULTILINE)]

    def rules(self, out, benchmarks, bmSuiteArgs):
        return [
            SulongBenchmarkRule({
                "benchmark": ("<benchmark>", str),
                "metric.name": "time",
                "metric.type": "numeric",
                "metric.value": ("<score>", float),
                "metric.score-function": "id",
                "metric.better": "lower",
                "metric.iteration": 0,
            }),
        ]

    def workingDirectory(self, benchmarks, bmSuiteArgs):
        if len(benchmarks) != 1:
            mx.abort(
                "Please run a specific benchmark (mx benchmark csuite:<benchmark-name>) or all the benchmarks (mx benchmark csuite:*)")
        vm = self.get_vm_registry().get_vm_from_suite_args(bmSuiteArgs)
        assert isinstance(vm, CExecutionEnvironmentMixin)
        return join(_benchmarksDirectory(), benchmarks[0], vm.bin_dir())

    def createCommandLineArgs(self, benchmarks, runArgs):
        if len(benchmarks) != 1:
            mx.abort("Please run a specific benchmark (mx benchmark csuite:<benchmark-name>) or all the benchmarks (mx benchmark csuite:*)")
        return [self.bench_to_exec[benchmarks[0]]]

    def get_vm_registry(self):
        return native_vm_registry


class CExecutionEnvironmentMixin(object):

    def bin_dir(self):
        return '{}-{}'.format(self.name(), self.config_name())

    def prepare_env(self, env):
        return env

    def post_process_executable(self, exe, *args, **kwargs):
        return exe


class GccLikeVm(CExecutionEnvironmentMixin, Vm):
    def __init__(self, config_name, options):
        self._config_name = config_name
        self.options = options

    def config_name(self):
        return self._config_name

    def c_compiler(self):
        return self.compiler_name()

    def cpp_compiler(self):
        return self.compiler_name() + "++"

    def compiler_name(self):
        mx.nyi()

    def c_compiler_exe(self):
        mx.nyi()

    def run(self, cwd, args):
        with tempfile.TemporaryFile(mode="w+") as f:
            try:
                myStdOut = mx.OutputCapture()
                retCode = mx.run(args, out=myStdOut, err=f)
            except BaseException as e:
                f.flush()
                f.seek(0)
                mx.logv(f.read())
                raise e

        return [retCode, myStdOut.data]

    def prepare_env(self, env):
        env['CFLAGS'] = ' '.join(self.options + _env_flags + ['-lm', '-lgmp'])
        env['CC'] = self.c_compiler_exe()
        return env


class GccVm(GccLikeVm):
    def __init__(self, config_name, options):
        super(GccVm, self).__init__(config_name, options)

    def name(self):
        return "gcc"

    def compiler_name(self):
        return "gcc"

    def c_compiler_exe(self):
        return "gcc"


class ClangVm(GccLikeVm):
    def __init__(self, config_name, options):
        super(ClangVm, self).__init__(config_name, options)

    def name(self):
        return "clang"

    def compiler_name(self):
        mx_sulong.ensureLLVMBinariesExist()
        return mx_sulong.findLLVMProgram(mx_buildtools.ClangCompiler.CLANG)

    def c_compiler_exe(self):
        return mx_buildtools.ClangCompiler.CLANG


class SulongVm(CExecutionEnvironmentMixin, GuestVm):
    def config_name(self):
        return "default"

    def name(self):
        return "sulong"

    def run(self, cwd, args):
        launcher_args = self.launcher_args()
        if hasattr(self.host_vm(), 'run_lang'):
            result = self.host_vm().run_lang('lli', launcher_args + args, cwd)
        else:
            sulongCmdLine = mx_sulong.getClasspathOptions() + \
                            ['-XX:-UseJVMCIClassLoader', "com.oracle.truffle.llvm.launcher.LLVMLauncher"]
            result = self.host_vm().run(cwd, sulongCmdLine + launcher_args + args)
        return result

    def prepare_env(self, env):
        env['CFLAGS'] = ' '.join(_env_flags + ['-lm', '-lgmp'])
        env['LLVM_COMPILER'] = mx_buildtools.ClangCompiler.CLANG
        env['CC'] = 'wllvm'
        return env

    def post_process_executable(self, exe, *args, **kwargs):
        bc_out = self.extract_bitcode(exe, *args, **kwargs)
        return self.optimize_bitcode(bc_out, *args, **kwargs)

    def extract_bitcode(self, native_out, *args, **kwargs):
        bc_out = 'bench.bc'
        mx.run(['extract-bc', native_out, '--output', bc_out], *args, **kwargs)
        return bc_out

    def optimize_bitcode(self, bc_out, *args, **kwargs):
        mx_sulong.opt(['-o', bc_out, bc_out] + self.opt_phases(), *args, **kwargs)
        return bc_out

    def opt_phases(self):
        return [
            '-mem2reg',
            '-globalopt',
            '-simplifycfg',
            '-constprop',
            '-instcombine',
            '-dse',
            '-loop-simplify',
            '-reassociate',
            '-licm',
            '-gvn',
        ]

    def launcher_args(self):
        launcher_args = [
            '--jvm.Dgraal.TruffleBackgroundCompilation=false',
            '--jvm.Dgraal.TruffleInliningMaxCallerSize=10000',
            '--jvm.Dgraal.TruffleCompilationExceptionsAreFatal=true',
            mx_subst.path_substitutions.substitute('--llvm.libraryPath=<path:SULONG_LIBS>'),
            '--llvm.libraries=libgmp.so.10']
        # FIXME: currently we do we do not support a common option prefix for jvm and native mode (GR-11165)
        if self.host_vm().config_name() == "native":
            def _convert_arg(arg):
                jvm_prefix = "--jvm."
                if arg.startswith(jvm_prefix):
                    return "--native." + arg[len(jvm_prefix):]
                return arg

            launcher_args = [_convert_arg(arg) for arg in launcher_args]

        return launcher_args

    def hosting_registry(self):
        return java_vm_registry

_suite = mx.suite("sulong")

native_vm_registry = VmRegistry("Native", known_host_registries=[java_vm_registry])
native_vm_registry.add_vm(GccVm('O0', ['-O0']), _suite)
native_vm_registry.add_vm(ClangVm('O0', ['-O0']), _suite)
native_vm_registry.add_vm(GccVm('O1', ['-O1']), _suite)
native_vm_registry.add_vm(ClangVm('O1', ['-O1']), _suite)
native_vm_registry.add_vm(GccVm('O2', ['-O2']), _suite)
native_vm_registry.add_vm(ClangVm('O2', ['-O2']), _suite)
native_vm_registry.add_vm(GccVm('O3', ['-O3']), _suite)
native_vm_registry.add_vm(ClangVm('O3', ['-O3']), _suite)
native_vm_registry.add_vm(SulongVm(), _suite, 10)
