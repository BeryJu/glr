#!/usr/bin/env python3
"""Run Scripts from .gitlab-ci.yml file locally"""

import argparse
import os
import subprocess
import sys

import yaml

T_GREEN = '\033[32m'
T_YELLOW = '\033[93m'
T_RED = '\033[91m'
T_DIM = '\033[37m'
T_RESET = '\033[m'

def log(color, level, text):
    """Print text with pretty colors and indented to level"""
    prefix = ' '.ljust(level)
    return print("%s ↳ %s%s%s" % (prefix, color, text, T_RESET))

class GitLabCIFile:
    """Operations around reading and parsing the .gitlab-ci.yml file"""

    _obj = None
    targets = []
    hide_output = False
    dry_run = False

    def __init__(self, full_path):
        with open(full_path, 'r') as _yaml_file:
            self._obj = yaml.safe_load(_yaml_file.read())

    def _extract_targets(self):
        """Extract list of targets"""
        targets = self._obj.get('stages', [])
        for key, value in self._obj.items():
            if 'script' in value:
                full_key = key
                if 'stage' in value:
                    full_key = "%s:%s" % (value.get('stage'), key)
                targets.append(full_key)
        return targets

    # pylint: disable=no-self-use
    def _run_command(self, cmd):
        """Wrapper to run command and redirect output"""
        log(T_DIM, 12, "Running %s" % cmd)
        if self.dry_run:
            log(T_YELLOW, 12, "Dry-Run enabled")
            return 0
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output, error = process.communicate()
        color = T_GREEN
        if process.returncode > 0:
            color = T_RED
        if not self.hide_output:
            log(color, 12, "stdout: '%s'" % output.decode('utf-8').rstrip("\n\r"))
            log(color, 12, "stderr: '%s'" % error.decode('utf-8').rstrip("\n\r"))
        log(color, 12, "Exit code: %d" % process.returncode)
        return process.returncode

    # pylint: disable=no-self-use
    def _to_array(self, value):
        """Take value and make sure it's an array"""
        if not isinstance(value, list):
            return [value]
        return value

    def resolve_target_names(self, target):
        """Resolve stage and stage:target names into list of targets"""
        targets = []
        # Target can either be <name> or <stage>:<name>
        if ':' in target:
            _, target = target.split(':')
        if 'stages' in self._obj and target in self._obj['stages']:
            sub_targets = []
            for _target in self.targets:
                if _target.startswith('%s:' % target):
                    sub_targets.append(_target.split(':')[1])
            log(T_DIM, 4, 'Stage %s implicitly triggers %r' % (target, sub_targets))
            targets += sub_targets
        else:
            targets.append(target)
        return targets

    def run_global_script(self, which):
        """Run global before_script/after_script if set"""
        key = '%s_script' % which
        log(T_DIM, 4, "Running global scripts")
        log(T_DIM, 8, key)
        return_code = 0
        if key in self._obj:
            sub_stage_rc = self._run_list(self._obj[key])
            return_code += sub_stage_rc
            # If command failed, don't run subsequent stages
            if sub_stage_rc > 0:
                return return_code
        return return_code

    def _run_list(self, commands):
        """Wrapper to call all commands in list and return their total return code"""
        # Run all commands in stage
        return_code = 0
        for command in self._to_array(commands):
            sub_stage_rc = self._run_command(command)
            return_code += sub_stage_rc
            # If command failed, don't run subsequent stages
            if sub_stage_rc > 0:
                return return_code
        return return_code

    def run(self, target_name):
        """Run target command"""
        sub_stages = ['before_script', 'script', 'after_script']
        return_code = 0
        for sub_stage in sub_stages:
            if sub_stage in self._obj[target_name]:
                log(T_DIM, 8, "Sub-stage '%s'" % sub_stage)
                # Run all commands in stage
                sub_stage_rc = self._run_list(self._obj[target_name][sub_stage])
                return_code += sub_stage_rc
                # If command failed, don't run subsequent stages
                if sub_stage_rc > 0:
                    return return_code
        return return_code

    def parse(self):
        """Run all parsing logic"""
        self.targets = self._extract_targets()

def main(args):
    """Main Logic"""
    file = args.file
    if not os.path.isabs(file):
        file = os.path.join(os.getcwd(), file)

    log(T_DIM, 0, "Loading file '%s'" % file)
    gitlab_ci = GitLabCIFile(file)
    gitlab_ci.hide_output = args.hide_output
    gitlab_ci.dry_run = args.dry_run
    gitlab_ci.parse()

    targets = args.target
    if not targets:
        if 'test' in gitlab_ci.targets:
            targets = ['test']
            log(T_DIM, 0, "No targets specified, Stage 'test' found; running test.")
        else:
            targets = gitlab_ci.targets
            log(T_DIM, 0, "No targets specified, running all.")

    return_code = gitlab_ci.run_global_script('before')

    log(T_GREEN, 0, "Running %d stage(s)" % len(targets))

    for target_to_run in targets:
        log(T_GREEN, 0, "Running Stage '%s'" % target_to_run)
        # Check if all targets that should be run exist
        if target_to_run not in gitlab_ci.targets:
            log(T_RED, 0, "Target '%s' does not exist, skipping" % target_to_run)
            return_code += 1
            continue

        for target in gitlab_ci.resolve_target_names(target_to_run):
            log(T_GREEN, 4, "Target '%s'" % target)
            try:
                gitlab_ci.run(target)
            except KeyError as exc:
                log(T_RED, 4, "Error: %r" % exc)

    return_code += gitlab_ci.run_global_script('after')

    final_message_color = T_RED if return_code > 0 else T_GREEN
    log(final_message_color, 0, "Exit Code: %d" % return_code)
    return return_code

def entrypoint():
    """Main entrypoint"""
    parser = argparse.ArgumentParser(description='Run .gitlab-ci.yml scripts locally.')
    parser.add_argument('target', type=str, default=[], nargs='*',
                        help=('Name of target to run. Can be name of target'
                              ', name of stage or stage:target.'))
    parser.add_argument('--file', type=str, default='.gitlab-ci.yml',
                        help='Path to .gitlab-ci.yml, defaults to ./.gitlab-ci.yml')
    parser.add_argument('--hide-output', action='store_true',
                        help='Optionally hide output of commands')
    parser.add_argument('--dry-run', action='store_true',
                        help="Don't actually run commands, just show them.")

    args = parser.parse_args()
    main(args)


if __name__ == '__main__':
    sys.exit(entrypoint())
