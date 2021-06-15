from box import Box, BoxKeyError
import sys
from collections import OrderedDict
from argparse import ArgumentParser, SUPPRESS
import os
import yaml

if not sys.warnoptions:
    import warnings
    warnings.simplefilter("always")


def represent_dictionary_order(self, dict_data):
    return self.represent_mapping('tag:yaml.org,2002:map', dict_data.items())


def setup_yaml():
    yaml.add_representer(OrderedDict, represent_dictionary_order)


setup_yaml()


class CargBox:
    def __init__(self, save_path, argparse, main_parser=None):
        self._config = {}
        arg_kwargs = {}
        if isinstance(argparse, ArgumentParser):
            arg_kwargs['parents'] = [argparse]
            if argparse.add_help:
                arg_kwargs['add_help'] = False
        self._config['argparse'] = ArgumentParser(**arg_kwargs)
        self._args = None

        self.main_parser = main_parser


        if save_path is not None:
            self._config['save_path'] = save_path

    def parse_partial(self):
        temp = ArgumentParser(add_help=False, parents=[self._config['argparse']])
        for action in temp._actions:
            if len(action.option_strings) == 0:
                action.required = False
        temp_args = OrderedDict(vars(temp.parse_args()))
        temp_args = OrderedDict({k: v for k, v in temp_args.items() if v is not None})
        not_loaded = {action.dest for action in self._config['argparse']._actions if action.dest not in temp_args.keys()}
        return temp_args, not_loaded

    def get_ordered_keys(self):
        ordered_keys = []
        for k in self._config['argparse']._actions:
            if k.dest is not SUPPRESS and k.default is not SUPPRESS:
                ordered_keys.append(k.dest)
        return ordered_keys

    def parse_args(self, *args, **kwargs):
        if self.main_parser is None:
            args = self._config['argparse'].parse_args(*args, **kwargs)
        else:
            args = self.main_parser.parse_args(*args, **kwargs)

        args = vars(args)
        self._args = Box()

        for key in self.get_ordered_keys():
            self._args[key] = args[key]

    def maybe_restore(self, save=False, update=False):
        yaml_path = os.path.join(self._config['save_path'], 'args.yaml')
        if os.path.exists(yaml_path):
            if not update:
                self.restore_from_yaml(show_diff=False)
            else:
                a, log = self.diff(only_changed=True, print_result=True)
                self.restore_from_yaml(show_diff=False)

                for k, v in log.added.items():
                    self._args[k] = v
                    #print("added %s: %s" % (k, v))

                for k, v in log.changed.items():
                    self._args[k] = v
                    #print("changed %s: %s" % (k, v))

                for k, v in log.deleted.items():
                    self._args[k] = v
                    warnings.warn("[arg deprecated]: %s. This option maybe deleted in the near future" % k, DeprecationWarning)

                if save and len(a.keys()) > 0:
                    self.save_to_yaml(show_diff=False)

        else:
            if self._args is None:
                self.parse_args()
            if save:
                self.save_to_yaml()

    @property
    def args(self):
        if self._args is None:
            self.parse_args()
        d = OrderedDict()
        for k in self.get_ordered_keys():
            try:
                d[k] = self._args[k]
            except KeyError:
                pass

        args = Box(ordered_box=True)

        try:
            del args.ordered_box
        except BoxKeyError:
            pass

        for k, v in d.items():
            args[k] = v

        return args

    def restore_from_yaml(self, show_diff=True):
        args = Box()

        not_loaded = {}
        if self._args is None:
            self._args, not_loaded = self.parse_partial()

            for k, v in self._args.items():
                args[k] = v

            _, log = self.diff(print_result=False)
            self._args = None
        else:
            for k, v in self._args.items():
                args[k] = v

            _, log = self.diff(print_result=show_diff)
        print("Restore arguments from %s" % os.path.join(self._config['save_path'], 'args.yaml'))
        yaml_path = os.path.join(self._config['save_path'], 'args.yaml')
        key_order = [k.dest for k in self._config['argparse']._actions
                     if k.dest is not SUPPRESS and k.default is not SUPPRESS]


        with open(yaml_path) as f:
            temp = Box.from_yaml(f.read())
            for key in key_order:
                try:
                    args[key] = temp[key]
                except BoxKeyError:
                    pass

        for k, v in log.deleted.items():
            args[k] = v
            if k not in not_loaded:
                warnings.warn("[arg deprecated]: %s. This option maybe deleted in the near future" % k, DeprecationWarning)

        self._args = args

    def save_to_yaml(self, save_main_parser: bool = False):
        os.makedirs(self._config['save_path'], exist_ok=True)
        with open(os.path.join(self._config['save_path'], 'args.yaml'), 'w') as f:
            yaml.dump(self.to_ordered_dict(), f)

        if save_main_parser and self.main_parser is not None:
            args = self.main_parser.parse_args()
            with open(os.path.join(self._config['save_path'], 'main_args.yaml'), 'w') as f:
                yaml.dump(OrderedDict(vars(args)), f)

    def to_ordered_dict(self):
        args = self.args.to_dict()
        ordered_args = OrderedDict()
        for key in self.get_ordered_keys():
            ordered_args[key] = args[key]
        return ordered_args

    def dump_yaml(self):
        return yaml.dump(self.to_ordered_dict())

    def diff(self, only_changed=True, print_result=True):
        new_keys = set(self.args.keys())

        yaml_path = os.path.join(self._config['save_path'], 'args.yaml')
        with open(yaml_path) as f:
            old = Box.from_yaml(f.read())

        old_keys = set(old.keys())

        k_added = new_keys - old_keys
        k_deleted = old_keys - new_keys

        added = {}
        deleted = {}
        changed = {}
        out = Box()
        for k, v in old.items():
            if k in k_deleted:
                out["%s (deleted)" % k] = "%s -> None" % str(v)
                deleted[k] = v
            elif v == self.args[k]:
                if not only_changed:
                    out[k] = self.args[k]
            else:
                out[k] = "%s -> %s" % (old[k], self.args[k])
                changed[k] = self.args[k]

        for k in k_added:
            out["%s (added)" % k] = self.args[k]
            added[k] = self.args[k]

        if print_result:
            if len(out.keys()) > 0:
                print("=======ARG CHANGED=======")
                print (out.to_yaml(), end="")
                print("=========================")
            else:
                print("No args are changed from %s" % yaml_path)
        return out, Box({'added': added, 'deleted': deleted, 'changed': changed})
