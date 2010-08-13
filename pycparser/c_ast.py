import c_ast as current
from ast import *

classes = [SubNodeClass('ArrayDecl',
                        children=['type','dim']),


           SubNodeClass('ArrayRef',
                        children=['name',
                                  'subscript']),

           SubNodeClass('Assignment',
                        ['op'],
                        ['lvalue',
                         'rvalue']),

           SubNodeClass('BinaryOp',
                        ['op'],
                        ['left', 'right']),

           SubNodeClass('Break'),

           SubNodeClass('Case',
                        children=['expr','stmt']),

           SubNodeClass('Cast',
                        children=['to_type',
                                  'expr']),

           SubNodeClass('Compound',
                        children=['decls',
                                  'stmts']),

           SubNodeClass('Constant',
                        ['type',
                         'value']),

           SubNodeClass('Conitnue'),

           SubNodeClass('Decl',
                        ['name',
                         'quals',
                         'storage'],
                        ['type',
                         'init',
                         'bitsize']),

           SubNodeClass('Default',
                        children = ['stmt']),


           SubNodeClass('DoWhile',
                        children = ['cond',
                                    'stmt']),

           SubNodeClass('EllipsisParam'),

           SubNodeClass('Enum',
                        ['name'],
                        ['values']),

           SubNodeClass('Enumerator',
                        ['name'],
                        ['value']),


           SubNodeClass('EnumeratorList',
                        children=['enumerators']),

           SubNodeClass('ExprList',
                        children=['exprs']),


           SubNodeClass('AST',
                        children=['ext']),

           SubNodeClass('For',
                        children=['init',
                                  'cond',
                                  'next',
                                  'stmt']),

           SubNodeClass('FuncCall',
                        children=['name',
                                  'args']),

           SubNodeClass('FuncDecl',
                        children=['args',
                                  'type']),

           SubNodeClass('FuncDef',
                        children=['decl',
                                  'body',
                                  'param_decls']),

           SubNodeClass('Goto', ['name']),

           SubNodeClass('ID', ['name']),

           SubNodeClass('IdentifierType', ['names']),

           SubNodeClass('If',
                        children = ['cond',
                                    'iftrue',
                                    'iffalse']),

           SubNodeClass('Label',
                        ['name'],
                        ['stmt']),

           SubNodeClass('ParamList',
                        children=['params']),

           SubNodeClass('PtrDecl', ['quals'], ['type']),

           SubNodeClass('Return',
                        children=['expr']),


           SubNodeClass('Struct', ['name'], ['decls']),

           SubNodeClass('StructRef',
                        ['type'],
                        ['name',
                         'field']),

           SubNodeClass('Switch',
                        children=['cond',
                                  'stmt']),


           SubNodeClass('TernaryOp',
                        children=['cond',
                                  'iftrue',
                                  'iffalse']),

           SubNodeClass('TypeDecl',
                        ['declname',
                         'quals'],
                        ['type']),

           SubNodeClass('Typedef',
                        ['name',
                         'quals',
                         'storage'],
                        ['type']),

           SubNodeClass('Typename',
                        ['quals'],
                        ['type']),

           SubNodeClass('UnaryOp', ['op'], ['expr']),

           SubNodeClass('Union', ['name'], ['decls']),

           SubNodeClass('While',
                        children = ['cond',
                                    'stmt'])]

for subclass in classes:
    setattr(current, subclass.__name__, subclass)
