from __future__ import print_function

import json
import sys
import re

# This is not required if you've installed pycparser into
# your site-packages/ with setup.py
#
sys.path.extend(['.', '..'])

from pycparser import parse_file, c_ast, c_parser, c_generator

RE_CHILD_ARRAY = re.compile('(.*)\[(.*)\]')

class CJsonError(Exception):
    pass

def to_dict(node):
    """ Recursively convert an ast into a python dictionary. """

    klass = node.__class__
    attr_names = klass.attr_names

    result = {}
    result['node_class'] = klass.__name__
    for attr in klass.attr_names:
        result[attr] = getattr(node, attr)

    for child_name, child in node.children():
        # child strings are either simple (e.g. 'value') or arrays (e.g. 'block_items[1]')
        match = RE_CHILD_ARRAY.match(child_name)
        if match:
            array_name, array_index = match.groups()
            array_index = int(array_index)
            # arrays come in order, so we verify and append.
            result[array_name] = result.get(array_name, [])
            if array_index != len(result[array_name]):
                raise CJsonError('Internal ast error. Array {} out of order. '
                    'Expected index {}, got {}'.format(
                    array_name, len(result[array_name]), array_index))
            result[array_name].append(to_dict(child))
        else:
            result[child_name] = to_dict(child)

    return result


def to_json(node, **kwargs):
    return json.dumps(to_dict(node), **kwargs)


def file_to_json(filename, **kwargs):
    ast = parse_file(filename, use_cpp=True)
    return to_json(ast, **kwargs)


#------------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
       print(file_to_json(sys.argv[1], sort_keys=True, indent=4))

    else:
        print("Please provide a filename as argument")
