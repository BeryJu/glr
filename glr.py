#!/usr/bin/env python3
"""Run Scripts from .gitlab-ci.yml file locally"""

import argparse
import os
import subprocess

import yaml

T_GREEN = '\033[32m'
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
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        output, _error = process.communicate()
        color = T_GREEN
        if process.returncode > 0:
            color = T_RED
        log(color, 12, "Output: '%s'" % output.decode('utf-8').rstrip("\n\r"))
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
        if ':' in target:
            _, target = target
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

    def run(self, target_name):
        """Run target command"""
        sub_stages = ['before_script', 'script', 'after_script']
        return_code = 0
        for sub_stage in sub_stages:
            if sub_stage in self._obj[target_name]:
                log(T_DIM, 8, "Sub-stage '%s'" % sub_stage)
                for command in self._to_array(self._obj[target_name][sub_stage]):
                    return_code += self._run_command(command)
        return return_code

    def parse(self):
        """Run all parsing logic"""
        self.targets = self._extract_targets()

def main(targets, file):
    """Main Logic"""
    if not os.path.isabs(file):
        file = os.path.join(os.getcwd(), file)
    log(T_DIM, 0, "Loading file '%s'" % file)
    gitlab_ci = GitLabCIFile(file)
    gitlab_ci.parse()

    if not targets:
        targets = gitlab_ci.targets
        log(T_DIM, 0, "No targets specified, running all.")

    log(T_GREEN, 0, "Running %d target(s)" % len(targets))

    for target_to_run in targets:
        # Check if all targets that should be run exist
        if not target_to_run in gitlab_ci.targets:
            log(T_RED, 0, "Target '%s' does not exist, skipping" % target_to_run)
            continue

        for target in gitlab_ci.resolve_target_names(target_to_run):
            log(T_GREEN, 4, "Target '%s'" % target)
            try:
                gitlab_ci.run(target)
            except KeyError as exc:
                log(T_RED, 4, "Error: %r" % exc)

if __name__ == '__main__':
    PARSER = argparse.ArgumentParser(description='Run .gitlab-ci.yml scripts locally.')
    PARSER.add_argument('target', type=str, default=[], nargs='*',
                        help=('Name of target to run. Can be name of target'
                              ', name of stage or stage:target.'))
    PARSER.add_argument('--file', type=str, default='.gitlab-ci.yml',
                        help='Path to .gitlab-ci.yml, defaults to ./.gitlab-ci.yml')

    ARGS = PARSER.parse_args()
    main(ARGS.target, ARGS.file)
