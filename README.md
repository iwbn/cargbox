# Configuration Arguments Box (CargBox)

## Example usage
```python
opt_parser = ArgumentParser(add_help=False)
opt_parser.add_argument('name', type=str)
opt_parser.add_argument('--seed', '-s', type=int, default=3)
opt_parser.add_argument('--ckpt', type=str, default='a/b/c3.ckpt')
opt_parser.add_argument('--opt1', type=str, default='190', choices=['190', '417'])
opt_parser.add_argument('--tf2', action='store_true')
opt_parser.add_argument('--tf', action='store_true')
opt_parser.add_argument('--tf3', action='store_true')

main_parser = ArgumentParser(parents=[opt_parser])
main_parser.add_argument("ckpt_path")
main_parser.add_argument("--update_args", action="store_true")

command_line_args = ["myModel", ".", "--update_args"]

args = main_parser.parse_args(command_line_args)

cargbox = CargBox(save_path=args.ckpt_path, argparse=opt_parser, main_parser=main_parser)
cargbox.parse_args(command_line_args)
print(cargbox.dump_yaml())

args = cargbox.args

print(args.tf)
```

* Save: `cargbox.save_to_yaml()` will save to the `save_path/args.yaml`
* Restore
  * `cargbox.maybe_restore()`: restore if `save_path/args.yaml` exist, otherwise, initialize args.
  * `cargbox.restore_from_yaml()`: restore from `save_path/args.yaml`. Raise error if file not exist.

