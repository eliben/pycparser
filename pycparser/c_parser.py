#------------------------------------------------------------------------------
# pycparser: c_parser.py
#
# CParser class: Parser and AST builder for the C language
#
# Copyright (C) 2008-2012, Eli Bendersky
# License: BSD
#------------------------------------------------------------------------------
import re

from .ply import yacc

from . import c_ast
from .c_lexer import CLexer
from .plyparser import PLYParser, Coord, ParseError
from .ast_transforms import fix_switch_cases


class CParser(PLYParser):    
    def __init__(
            self, 
            lex_optimize=True,
            lextab='pycparser.lextab',
            yacc_optimize=True,
            yacctab='pycparser.yacctab',
            yacc_debug=False):
        """ Create a new CParser.
        
            Some arguments for controlling the debug/optimization
            level of the parser are provided. The defaults are 
            tuned for release/performance mode. 
            The simple rules for using them are:
            *) When tweaking CParser/CLexer, set these to False
            *) When releasing a stable parser, set to True
            
            lex_optimize:
                Set to False when you're modifying the lexer.
                Otherwise, changes in the lexer won't be used, if
                some lextab.py file exists.
                When releasing with a stable lexer, set to True
                to save the re-generation of the lexer table on 
                each run.
            
            lextab:
                Points to the lex table that's used for optimized
                mode. Only if you're modifying the lexer and want
                some tests to avoid re-generating the table, make 
                this point to a local lex table file (that's been
                earlier generated with lex_optimize=True)
            
            yacc_optimize:
                Set to False when you're modifying the parser.
                Otherwise, changes in the parser won't be used, if
                some parsetab.py file exists.
                When releasing with a stable parser, set to True
                to save the re-generation of the parser table on 
                each run.
            
            yacctab:
                Points to the yacc table that's used for optimized
                mode. Only if you're modifying the parser, make 
                this point to a local yacc table file
                        
            yacc_debug:
                Generate a parser.out file that explains how yacc
                built the parsing table from the grammar.
        """
        self.clex = CLexer(
            error_func=self._lex_error_func,
            type_lookup_func=self._lex_type_lookup_func)
            
        self.clex.build(
            optimize=lex_optimize,
            lextab=lextab)
        self.tokens = self.clex.tokens
        
        rules_with_opt = [
            'abstract_declarator',
            'assignment_expression',
            'declaration_list',
            'declaration_specifiers',
            'designation',
            'expression',
            'identifier_list',
            'init_declarator_list',
            'parameter_type_list',
            'specifier_qualifier_list',
            'block_item_list',
            'type_qualifier_list',
            'struct_declarator_list'
        ]
        
        for rule in rules_with_opt:
            self._create_opt_rule(rule)
        
        self.cparser = yacc.yacc(
            module=self, 
            start='translation_unit_or_empty',
            debug=yacc_debug,
            optimize=yacc_optimize,
            tabmodule=yacctab)
        
        # Stack of scopes for keeping track of typedefs. _scope_stack[-1] is
        # the current (topmost) scope.
        #
        self._scope_stack = [set()]
    
    def parse(self, text, filename='', debuglevel=0):
        """ Parses C code and returns an AST.
        
            text:
                A string containing the C source code
            
            filename:
                Name of the file being parsed (for meaningful
                error messages)
            
            debuglevel:
                Debug level to yacc
        """
        self.clex.filename = filename
        self.clex.reset_lineno()
        self._scope_stack = [set()]
        return self.cparser.parse(text, lexer=self.clex, debug=debuglevel)
    
    ######################--   PRIVATE   --######################
    
    def _push_scope(self):
        self._scope_stack.append(set())

    def _pop_scope(self):
        assert len(self._scope_stack) > 1
        self._scope_stack.pop()

    def _add_typedef_type(self, name):
        """ Add a new typedef-name to the current scope
        """
        self._scope_stack[-1].add(name)
        #~ print(self._scope_stack)

    def _is_type_in_scope(self, name):
        """ Is *name* a typedef-name in the current scope?
        """
        return any(name in scope for scope in self._scope_stack)

    def _lex_error_func(self, msg, line, column):
        self._parse_error(msg, self._coord(line, column))
    
    def _lex_type_lookup_func(self, name):
        """ Looks up types that were previously defined with
            typedef. 
            Passed to the lexer for recognizing identifiers that
            are types.
        """
        return self._is_type_in_scope(name)
    
    # To understand what's going on here, read sections A.8.5 and 
    # A.8.6 of K&R2 very carefully.
    # 
    # A C type consists of a basic type declaration, with a list
    # of modifiers. For example:
    #
    # int *c[5];
    #
    # The basic declaration here is 'int c', and the pointer and
    # the array are the modifiers.
    #
    # Basic declarations are represented by TypeDecl (from module
    # c_ast) and the modifiers are FuncDecl, PtrDecl and 
    # ArrayDecl.
    #
    # The standard states that whenever a new modifier is parsed,
    # it should be added to the end of the list of modifiers. For
    # example:
    #
    # K&R2 A.8.6.2: Array Declarators
    #
    # In a declaration T D where D has the form  
    #   D1 [constant-expression-opt]  
    # and the type of the identifier in the declaration T D1 is 
    # "type-modifier T", the type of the 
    # identifier of D is "type-modifier array of T"
    #
    # This is what this method does. The declarator it receives
    # can be a list of declarators ending with TypeDecl. It 
    # tacks the modifier to the end of this list, just before 
    # the TypeDecl.
    #
    # Additionally, the modifier may be a list itself. This is 
    # useful for pointers, that can come as a chain from the rule
    # p_pointer. In this case, the whole modifier list is spliced 
    # into the new location.
    #
    def _type_modify_decl(self, decl, modifier):
        """ Tacks a type modifier on a declarator, and returns
            the modified declarator.
            
            Note: the declarator and modifier may be modified
        """
        #~ print '****'
        #~ decl.show(offset=3)
        #~ modifier.show(offset=3)
        #~ print '****'
        
        modifier_head = modifier
        modifier_tail = modifier
        
        # The modifier may be a nested list. Reach its tail.
        #
        while modifier_tail.type: 
            modifier_tail = modifier_tail.type
        
        # If the decl is a basic type, just tack the modifier onto
        # it
        #
        if isinstance(decl, c_ast.TypeDecl):
            modifier_tail.type = decl
            return modifier
        else:
            # Otherwise, the decl is a list of modifiers. Reach
            # its tail and splice the modifier onto the tail,
            # pointing to the underlying basic type.
            #
            decl_tail = decl
            
            while not isinstance(decl_tail.type, c_ast.TypeDecl):
                decl_tail = decl_tail.type
            
            modifier_tail.type = decl_tail.type
            decl_tail.type = modifier_head
            return decl

    # Due to the order in which declarators are constructed,
    # they have to be fixed in order to look like a normal AST.
    # 
    # When a declaration arrives from syntax construction, it has
    # these problems:
    # * The innermost TypeDecl has no type (because the basic
    #   type is only known at the uppermost declaration level)
    # * The declaration has no variable name, since that is saved
    #   in the innermost TypeDecl
    # * The typename of the declaration is a list of type 
    #   specifiers, and not a node. Here, basic identifier types
    #   should be separated from more complex types like enums
    #   and structs.
    #
    # This method fixes these problem.
    #
    def _fix_decl_name_type(self, decl, typename):
        """ Fixes a declaration. Modifies decl.
        """
        # Reach the underlying basic type
        #
        type = decl
        while not isinstance(type, c_ast.TypeDecl):
            type = type.type
        
        decl.name = type.declname
        type.quals = decl.quals
        
        # The typename is a list of types. If any type in this 
        # list isn't an IdentifierType, it must be the only
        # type in the list (it's illegal to declare "int enum .."
        # If all the types are basic, they're collected in the
        # IdentifierType holder.
        #
        for tn in typename:
            if not isinstance(tn, c_ast.IdentifierType):
                if len(typename) > 1:
                    self._parse_error(
                        "Invalid multiple types specified", tn.coord)
                else:
                    type.type = tn
                    return decl
        
        # At this point, we know that typename is a list of IdentifierType
        # nodes. Concatenate all the names into a single list.
        type.type = c_ast.IdentifierType(
            [name for id in typename for name in id.names],
            coord=typename[0].coord)
        return decl
    
    def _add_declaration_specifier(self, declspec, newspec, kind):
        """ Declaration specifiers are represented by a dictionary
            with the entries:
            * qual: a list of type qualifiers
            * storage: a list of storage type qualifiers
            * type: a list of type specifiers
            * function: a list of function specifiers
            
            This method is given a declaration specifier, and a 
            new specifier of a given kind.
            Returns the declaration specifier, with the new 
            specifier incorporated.
        """
        spec = declspec or dict(qual=[], storage=[], type=[], function=[])
        spec[kind].insert(0, newspec)
        return spec
    
    def _build_function_definition(self, decl, spec, param_decls, body):
        """ Builds a function definition.
        """
        declaration = c_ast.Decl(
            name=None,
            quals=spec['qual'],
            storage=spec['storage'],
            funcspec=spec['function'],
            type=decl, 
            init=None, 
            bitsize=None, 
            coord=decl.coord)
        
        typename = spec['type']
        declaration = self._fix_decl_name_type(declaration, typename)
        return c_ast.FuncDef(
            decl=declaration,
            param_decls=param_decls,
            body=body,
            coord=decl.coord)

    def _select_struct_union_class(self, token):
        """ Given a token (either STRUCT or UNION), selects the
            appropriate AST class.
        """
        if token == 'struct':
            return c_ast.Struct
        else:
            return c_ast.Union

    ##
    ## Precedence and associativity of operators
    ##
    precedence = (
        ('left', 'LOR'),
        ('left', 'LAND'),
        ('left', 'OR'),
        ('left', 'XOR'),
        ('left', 'AND'),
        ('left', 'EQ', 'NE'),
        ('left', 'GT', 'GE', 'LT', 'LE'),
        ('left', 'RSHIFT', 'LSHIFT'),
        ('left', 'PLUS', 'MINUS'),
        ('left', 'TIMES', 'DIVIDE', 'MOD')
    )

    ##
    ## Grammar productions
    ## Implementation of the BNF defined in K&R2 A.13
    ##

    # Wrapper around a translation unit, to allow for empty input.
    # Not strictly part of the C99 Grammar, but useful in practice.
    #
    def p_translation_unit_or_empty(self, p):
        """ translation_unit_or_empty   : translation_unit
                                        | empty
        """
        if p[1] is None:
            p[0] = c_ast.FileAST([])
        else:
            p[0] = c_ast.FileAST(p[1])

    def p_translation_unit_1(self, p):
        """ translation_unit    : external_declaration 
        """
        # Note: external_declaration is already a list
        #
        p[0] = p[1]
    
    def p_translation_unit_2(self, p):
        """ translation_unit    : translation_unit external_declaration
        """
        if p[2] is not None:
            p[1].extend(p[2])
        p[0] = p[1]
    
    # Declarations always come as lists (because they can be
    # several in one line), so we wrap the function definition 
    # into a list as well, to make the return value of 
    # external_declaration homogenous.
    #
    def p_external_declaration_1(self, p):
        """ external_declaration    : function_definition
        """
        p[0] = [p[1]]
    
    def p_external_declaration_2(self, p):
        """ external_declaration    : declaration
        """
        p[0] = p[1]

    def p_external_declaration_3(self, p):
        """ external_declaration    : pp_directive
        """
        p[0] = p[1]
    
    def p_external_declaration_4(self, p):
        """ external_declaration    : SEMI
        """
        p[0] = None

    def p_pp_directive(self, p):
        """ pp_directive  : PPHASH 
        """
        self._parse_error('Directives not supported yet', 
            self._coord(p.lineno(1)))

    # In function definitions, the declarator can be followed by
    # a declaration list, for old "K&R style" function definitios.
    #
    def p_function_definition_1(self, p):
        """ function_definition : declarator declaration_list_opt compound_statement
        """
        # no declaration specifiers
        spec = dict(qual=[], storage=[], type=[])

        p[0] = self._build_function_definition(
            decl=p[1],
            spec=spec, 
            param_decls=p[2],
            body=p[3])
                    
    def p_function_definition_2(self, p):
        """ function_definition : declaration_specifiers declarator declaration_list_opt compound_statement
        """
        spec = p[1]

        p[0] = self._build_function_definition(
            decl=p[2],
            spec=spec, 
            param_decls=p[3],
            body=p[4])
        
    def p_statement(self, p):
        """ statement   : labeled_statement
                        | expression_statement
                        | compound_statement
                        | selection_statement
                        | iteration_statement    
                        | jump_statement
        """
        p[0] = p[1]

    # In C, declarations can come several in a line:
    #   int x, *px, romulo = 5;
    #
    # However, for the AST, we will split them to separate Decl
    # nodes.
    #
    # This rule splits its declarations and always returns a list
    # of Decl nodes, even if it's one element long.
    #
    def p_decl_body(self, p):
        """ decl_body : declaration_specifiers init_declarator_list_opt
        """
        spec = p[1]
        is_typedef = 'typedef' in spec['storage']
        decls = []
        
        # p[2] (init_declarator_list_opt) is either a list or None
        #
        if p[2] is None:
            # Then it's a declaration of a struct / enum tag,
            # without an actual declarator.
            #
            ty = spec['type']
            if len(ty) > 1:
                coord = '?'
                for t in ty:
                    if hasattr(t, 'coord'):
                        coord = t.coord
                        break
                        
                self._parse_error('Multiple type specifiers with a type tag',
                        coord)
            
            decl = c_ast.Decl(
                name=None,
                quals=spec['qual'],
                storage=spec['storage'],
                funcspec=spec['function'],
                type=ty[0],
                init=None,
                bitsize=None,
                coord=ty[0].coord)
            decls = [decl]
        else:
            for decl, init in p[2] or []:
                if is_typedef:
                    decl = c_ast.Typedef(
                        name=None,
                        quals=spec['qual'],
                        storage=spec['storage'],
                        type=decl,
                        coord=decl.coord)
                else:
                    decl = c_ast.Decl(
                        name=None,
                        quals=spec['qual'],
                        storage=spec['storage'],
                        funcspec=spec['function'],
                        type=decl, 
                        init=init, 
                        bitsize=None, 
                        coord=decl.coord)
                
                typename = spec['type']
                fixed_decl = self._fix_decl_name_type(decl, typename)

                # Add the type name defined by typedef to a
                # symbol table (for usage in the lexer)
                # 
                if is_typedef:
                    self._add_typedef_type(fixed_decl.name)

                decls.append(fixed_decl)

        p[0] = decls

    # The declaration has been split to a decl_body sub-rule and
    # SEMI, because having them in a single rule created a problem
    # for defining typedefs.
    #
    # If a typedef line was directly followed by a line using the
    # type defined with the typedef, the type would not be 
    # recognized. This is because to reduce the declaration rule,
    # the parser's lookahead asked for the token after SEMI, which
    # was the type from the next line, and the lexer had no chance
    # to see the updated type symbol table.
    #
    # Splitting solves this problem, because after seeing SEMI,
    # the parser reduces decl_body, which actually adds the new
    # type into the table to be seen by the lexer before the next
    # line is reached.
    #
    def p_declaration(self, p):
        """ declaration : decl_body SEMI 
        """
        p[0] = p[1]

    # Since each declaration is a list of declarations, this
    # rule will combine all the declarations and return a single
    # list
    # 
    def p_declaration_list(self, p):
        """ declaration_list    : declaration
                                | declaration_list declaration
        """
        p[0] = p[1] if len(p) == 2 else p[1] + p[2]
    
    def p_declaration_specifiers_1(self, p):
        """ declaration_specifiers  : type_qualifier declaration_specifiers_opt 
        """
        p[0] = self._add_declaration_specifier(p[2], p[1], 'qual')
        
    def p_declaration_specifiers_2(self, p):
        """ declaration_specifiers  : type_specifier declaration_specifiers_opt
        """
        p[0] = self._add_declaration_specifier(p[2], p[1], 'type')
        
    def p_declaration_specifiers_3(self, p):
        """ declaration_specifiers  : storage_class_specifier declaration_specifiers_opt
        """
        p[0] = self._add_declaration_specifier(p[2], p[1], 'storage')
        
    def p_declaration_specifiers_4(self, p):
        """ declaration_specifiers  : function_specifier declaration_specifiers_opt
        """
        p[0] = self._add_declaration_specifier(p[2], p[1], 'function')
    
    def p_storage_class_specifier(self, p):
        """ storage_class_specifier : AUTO
                                    | REGISTER
                                    | STATIC
                                    | EXTERN
                                    | TYPEDEF
        """
        p[0] = p[1]
    
    def p_function_specifier(self, p):
        """ function_specifier  : INLINE
        """
        p[0] = p[1]
    
    def p_type_specifier_1(self, p):
        """ type_specifier  : VOID
                            | _BOOL
                            | CHAR
                            | SHORT
                            | INT
                            | LONG
                            | FLOAT
                            | DOUBLE
                            | _COMPLEX
                            | SIGNED
                            | UNSIGNED
        """
        p[0] = c_ast.IdentifierType([p[1]], coord=self._coord(p.lineno(1)))

    def p_type_specifier_2(self, p):
        """ type_specifier  : typedef_name
                            | enum_specifier
                            | struct_or_union_specifier
        """
        p[0] = p[1]
    
    def p_type_qualifier(self, p):
        """ type_qualifier  : CONST
                            | RESTRICT
                            | VOLATILE
        """
        p[0] = p[1]
    
    def p_init_declarator_list(self, p):
        """ init_declarator_list    : init_declarator
                                    | init_declarator_list COMMA init_declarator
        """
        p[0] = p[1] + [p[3]] if len(p) == 4 else [p[1]]

    # Returns a (declarator, initializer) pair
    # If there's no initializer, returns (declarator, None)
    #
    def p_init_declarator(self, p):
        """ init_declarator : declarator
                            | declarator EQUALS initializer
        """
        p[0] = (p[1], p[3] if len(p) > 2 else None)        
    
    def p_specifier_qualifier_list_1(self, p):
        """ specifier_qualifier_list    : type_qualifier specifier_qualifier_list_opt
        """
        p[0] = self._add_declaration_specifier(p[2], p[1], 'qual')
        
    def p_specifier_qualifier_list_2(self, p):
        """ specifier_qualifier_list    : type_specifier specifier_qualifier_list_opt
        """
        p[0] = self._add_declaration_specifier(p[2], p[1], 'type')

    # TYPEID is allowed here (and in other struct/enum related tag names), because
    # struct/enum tags reside in their own namespace and can be named the same as types
    #
    def p_struct_or_union_specifier_1(self, p):
        """ struct_or_union_specifier   : struct_or_union ID
                                        | struct_or_union TYPEID
        """
        klass = self._select_struct_union_class(p[1])
        p[0] = klass(
            name=p[2], 
            decls=None, 
            coord=self._coord(p.lineno(2)))

    def p_struct_or_union_specifier_2(self, p):
        """ struct_or_union_specifier : struct_or_union brace_open struct_declaration_list brace_close
        """
        klass = self._select_struct_union_class(p[1])
        p[0] = klass(
            name=None,
            decls=p[3],
            coord=self._coord(p.lineno(2)))

    def p_struct_or_union_specifier_3(self, p):
        """ struct_or_union_specifier   : struct_or_union ID brace_open struct_declaration_list brace_close
                                        | struct_or_union TYPEID brace_open struct_declaration_list brace_close
        """
        klass = self._select_struct_union_class(p[1])
        p[0] = klass(
            name=p[2],
            decls=p[4],
            coord=self._coord(p.lineno(2)))

    def p_struct_or_union(self, p):
        """ struct_or_union : STRUCT 
                            | UNION
        """
        p[0] = p[1]

    # Combine all declarations into a single list
    #
    def p_struct_declaration_list(self, p):
        """ struct_declaration_list     : struct_declaration
                                        | struct_declaration_list struct_declaration
        """
        p[0] = p[1] if len(p) == 2 else p[1] + p[2]

    def p_struct_declaration_1(self, p):
        """ struct_declaration : specifier_qualifier_list struct_declarator_list_opt SEMI
        """
        spec = p[1]
        decls = []
        
        if p[2] is not None:
            for struct_decl in p[2]:
                if struct_decl['decl'] is not None:
                    decl_coord = struct_decl['decl'].coord
                else:
                    decl_coord = struct_decl['bitsize'].coord
            
                decl = c_ast.Decl(
                    name=None,
                    quals=spec['qual'],
                    funcspec=spec['function'],
                    storage=spec['storage'],
                    type=struct_decl['decl'],
                    init=None,
                    bitsize=struct_decl['bitsize'],
                    coord=decl_coord)
            
                typename = spec['type']
                decls.append(self._fix_decl_name_type(decl, typename))
        else:
            # Anonymous struct/union, gcc extension, C1x feature.
            # Although the standard only allows structs/unions here, I see no 
            # reason to disallow other types since some compilers have typedefs
            # here, and pycparser isn't about rejecting all invalid code.
            #             
            node = spec['type'][0]

            if isinstance(node, c_ast.Node):
                decl_type = node
            else:
                decl_type = c_ast.IdentifierType(node)
            
            decl = c_ast.Decl(
                name=None,
                quals=spec['qual'],
                funcspec=spec['function'],
                storage=spec['storage'],
                type=decl_type,
                init=None,
                bitsize=None,
                coord=self._coord(p.lineno(3)))
            decls.append(decl)
        
        p[0] = decls
    
    def p_struct_declarator_list(self, p):
        """ struct_declarator_list  : struct_declarator
                                    | struct_declarator_list COMMA struct_declarator
        """
        p[0] = p[1] + [p[3]] if len(p) == 4 else [p[1]]
    
    # struct_declarator passes up a dict with the keys: decl (for
    # the underlying declarator) and bitsize (for the bitsize)
    #
    def p_struct_declarator_1(self, p):
        """ struct_declarator : declarator
        """
        p[0] = {'decl': p[1], 'bitsize': None}
    
    def p_struct_declarator_2(self, p):
        """ struct_declarator   : declarator COLON constant_expression
                                | COLON constant_expression
        """
        if len(p) > 3:
            p[0] = {'decl': p[1], 'bitsize': p[3]}
        else:
            p[0] = {'decl': c_ast.TypeDecl(None, None, None), 'bitsize': p[2]}
    
    def p_enum_specifier_1(self, p):
        """ enum_specifier  : ENUM ID
                            | ENUM TYPEID
        """
        p[0] = c_ast.Enum(p[2], None, self._coord(p.lineno(1)))
    
    def p_enum_specifier_2(self, p):
        """ enum_specifier  : ENUM brace_open enumerator_list brace_close
        """
        p[0] = c_ast.Enum(None, p[3], self._coord(p.lineno(1)))
    
    def p_enum_specifier_3(self, p):
        """ enum_specifier  : ENUM ID brace_open enumerator_list brace_close
                            | ENUM TYPEID brace_open enumerator_list brace_close
        """
        p[0] = c_ast.Enum(p[2], p[4], self._coord(p.lineno(1)))
        
    def p_enumerator_list(self, p):
        """ enumerator_list : enumerator
                            | enumerator_list COMMA
                            | enumerator_list COMMA enumerator
        """
        if len(p) == 2:
            p[0] = c_ast.EnumeratorList([p[1]], p[1].coord)
        elif len(p) == 3:
            p[0] = p[1]
        else:
            p[1].enumerators.append(p[3])
            p[0] = p[1]

    def p_enumerator(self, p):
        """ enumerator  : ID
                        | ID EQUALS constant_expression
        """
        if len(p) == 2:
            p[0] = c_ast.Enumerator(
                        p[1], None, 
                        self._coord(p.lineno(1)))
        else:
            p[0] = c_ast.Enumerator(
                        p[1], p[3], 
                        self._coord(p.lineno(1)))
    
    def p_declarator_1(self, p):
        """ declarator  : direct_declarator 
        """
        p[0] = p[1]
    
    def p_declarator_2(self, p):
        """ declarator  : pointer direct_declarator 
        """
        p[0] = self._type_modify_decl(p[2], p[1])
    
    def p_direct_declarator_1(self, p):
        """ direct_declarator   : ID 
        """
        p[0] = c_ast.TypeDecl(
            declname=p[1], 
            type=None, 
            quals=None,
            coord=self._coord(p.lineno(1)))
        
    def p_direct_declarator_2(self, p):
        """ direct_declarator   : LPAREN declarator RPAREN 
        """
        p[0] = p[2]
        
    def p_direct_declarator_3(self, p):
        """ direct_declarator   : direct_declarator LBRACKET assignment_expression_opt RBRACKET 
        """
        arr = c_ast.ArrayDecl(
            type=None,
            dim=p[3],
            coord=p[1].coord)
        
        p[0] = self._type_modify_decl(decl=p[1], modifier=arr)

    # Special for VLAs
    #
    def p_direct_declarator_4(self, p):
        """ direct_declarator   : direct_declarator LBRACKET TIMES RBRACKET 
        """
        arr = c_ast.ArrayDecl(
            type=None,
            dim=c_ast.ID(p[3], self._coord(p.lineno(3))),
            coord=p[1].coord)
        
        p[0] = self._type_modify_decl(decl=p[1], modifier=arr)

    def p_direct_declarator_5(self, p):
        """ direct_declarator   : direct_declarator LPAREN parameter_type_list RPAREN 
                                | direct_declarator LPAREN identifier_list_opt RPAREN
        """
        func = c_ast.FuncDecl(
            args=p[3],
            type=None,
            coord=p[1].coord)
        
        p[0] = self._type_modify_decl(decl=p[1], modifier=func)
    
    def p_pointer(self, p):
        """ pointer : TIMES type_qualifier_list_opt
                    | TIMES type_qualifier_list_opt pointer
        """
        coord = self._coord(p.lineno(1))
        
        p[0] = c_ast.PtrDecl(
            quals=p[2] or [],
            type=p[3] if len(p) > 3 else None,
            coord=coord)
    
    def p_type_qualifier_list(self, p):
        """ type_qualifier_list : type_qualifier
                                | type_qualifier_list type_qualifier
        """
        p[0] = [p[1]] if len(p) == 2 else p[1] + [p[2]]
    
    def p_parameter_type_list(self, p):
        """ parameter_type_list : parameter_list
                                | parameter_list COMMA ELLIPSIS
        """
        if len(p) > 2: 
            p[1].params.append(c_ast.EllipsisParam(self._coord(p.lineno(3))))
        
        p[0] = p[1]

    def p_parameter_list(self, p):
        """ parameter_list  : parameter_declaration
                            | parameter_list COMMA parameter_declaration
        """
        if len(p) == 2: # single parameter
            p[0] = c_ast.ParamList([p[1]], p[1].coord)
        else:
            p[1].params.append(p[3])
            p[0] = p[1]

    def p_parameter_declaration_1(self, p):
        """ parameter_declaration   : declaration_specifiers declarator
        """
        spec = p[1]
        decl = p[2]
        
        decl = c_ast.Decl(
            name=None,
            quals=spec['qual'],
            storage=spec['storage'],
            funcspec=spec['function'],
            type=decl, 
            init=None, 
            bitsize=None, 
            coord=decl.coord)
        
        typename = spec['type'] or ['int']
        p[0] = self._fix_decl_name_type(decl, typename)
        
    def p_parameter_declaration_2(self, p):
        """ parameter_declaration   : declaration_specifiers abstract_declarator_opt
        """
        spec = p[1]
        decl = c_ast.Typename(
            quals=spec['qual'], 
            type=p[2] or c_ast.TypeDecl(None, None, None),
            coord=self._coord(p.lineno(2)))
            
        typename = spec['type'] or ['int']
        p[0] = self._fix_decl_name_type(decl, typename)        
    
    def p_identifier_list(self, p):
        """ identifier_list : identifier
                            | identifier_list COMMA identifier
        """
        if len(p) == 2: # single parameter
            p[0] = c_ast.ParamList([p[1]], p[1].coord)
        else:
            p[1].params.append(p[3])
            p[0] = p[1]

    def p_initializer_1(self, p):
        """ initializer : assignment_expression
        """
        p[0] = p[1]
    
    def p_initializer_2(self, p):
        """ initializer : brace_open initializer_list brace_close
                        | brace_open initializer_list COMMA brace_close
        """
        p[0] = p[2]

    def p_initializer_list(self, p):
        """ initializer_list    : designation_opt initializer
                                | initializer_list COMMA designation_opt initializer
        """
        if len(p) == 3: # single initializer
            init = p[2] if p[1] is None else c_ast.NamedInitializer(p[1], p[2])
            p[0] = c_ast.InitList([init], p[2].coord)
        else:
            init = p[4] if p[3] is None else c_ast.NamedInitializer(p[3], p[4])
            p[1].exprs.append(init)
            p[0] = p[1]
    
    def p_designation(self, p):
        """ designation : designator_list EQUALS
        """
        p[0] = p[1]
    
    # Designators are represented as a list of nodes, in the order in which
    # they're written in the code.
    #
    def p_designator_list(self, p):
        """ designator_list : designator
                            | designator_list designator
        """
        p[0] = [p[1]] if len(p) == 2 else p[1] + [p[2]]
    
    def p_designator(self, p):
        """ designator  : LBRACKET constant_expression RBRACKET
                        | PERIOD identifier
        """
        p[0] = p[2]
    
    def p_type_name(self, p):
        """ type_name   : specifier_qualifier_list abstract_declarator_opt 
        """
        #~ print '=========='
        #~ print p[1]
        #~ print p[2]
        #~ print p[2].children()
        #~ print '=========='
        
        typename = c_ast.Typename(
            quals=p[1]['qual'], 
            type=p[2] or c_ast.TypeDecl(None, None, None),
            coord=self._coord(p.lineno(2)))
        
        p[0] = self._fix_decl_name_type(typename, p[1]['type'])

    def p_abstract_declarator_1(self, p):
        """ abstract_declarator     : pointer
        """
        dummytype = c_ast.TypeDecl(None, None, None)
        p[0] = self._type_modify_decl(
            decl=dummytype, 
            modifier=p[1])
        
    def p_abstract_declarator_2(self, p):
        """ abstract_declarator     : pointer direct_abstract_declarator
        """
        p[0] = self._type_modify_decl(p[2], p[1])
        
    def p_abstract_declarator_3(self, p):
        """ abstract_declarator     : direct_abstract_declarator
        """
        p[0] = p[1]
    
    # Creating and using direct_abstract_declarator_opt here 
    # instead of listing both direct_abstract_declarator and the
    # lack of it in the beginning of _1 and _2 caused two 
    # shift/reduce errors.
    #
    def p_direct_abstract_declarator_1(self, p):
        """ direct_abstract_declarator  : LPAREN abstract_declarator RPAREN """
        p[0] = p[2]
    
    def p_direct_abstract_declarator_2(self, p):
        """ direct_abstract_declarator  : direct_abstract_declarator LBRACKET assignment_expression_opt RBRACKET 
        """
        arr = c_ast.ArrayDecl(
            type=None,
            dim=p[3],
            coord=p[1].coord)
        
        p[0] = self._type_modify_decl(decl=p[1], modifier=arr)
        
    def p_direct_abstract_declarator_3(self, p):
        """ direct_abstract_declarator  : LBRACKET assignment_expression_opt RBRACKET 
        """
        p[0] = c_ast.ArrayDecl(
            type=c_ast.TypeDecl(None, None, None),
            dim=p[2],
            coord=self._coord(p.lineno(1)))

    def p_direct_abstract_declarator_4(self, p):
        """ direct_abstract_declarator  : direct_abstract_declarator LBRACKET TIMES RBRACKET 
        """
        arr = c_ast.ArrayDecl(
            type=None,
            dim=c_ast.ID(p[3], self._coord(p.lineno(3))),
            coord=p[1].coord)
        
        p[0] = self._type_modify_decl(decl=p[1], modifier=arr)

    def p_direct_abstract_declarator_5(self, p):
        """ direct_abstract_declarator  : LBRACKET TIMES RBRACKET 
        """
        p[0] = c_ast.ArrayDecl(
            type=c_ast.TypeDecl(None, None, None),
            dim=c_ast.ID(p[3], self._coord(p.lineno(3))),
            coord=self._coord(p.lineno(1)))

    def p_direct_abstract_declarator_6(self, p):
        """ direct_abstract_declarator  : direct_abstract_declarator LPAREN parameter_type_list_opt RPAREN 
        """
        func = c_ast.FuncDecl(
            args=p[3],
            type=None,
            coord=p[1].coord)
        
        p[0] = self._type_modify_decl(decl=p[1], modifier=func)
        
    def p_direct_abstract_declarator_7(self, p):
        """ direct_abstract_declarator  : LPAREN parameter_type_list_opt RPAREN 
        """
        p[0] = c_ast.FuncDecl(
            args=p[2],
            type=c_ast.TypeDecl(None, None, None),
            coord=self._coord(p.lineno(1)))
    
    # declaration is a list, statement isn't. To make it consistent, block_item
    # will always be a list
    #
    def p_block_item(self, p):
        """ block_item  : declaration
                        | statement
        """
        p[0] = p[1] if isinstance(p[1], list) else [p[1]]
    
    # Since we made block_item a list, this just combines lists
    # 
    def p_block_item_list(self, p):
        """ block_item_list : block_item 
                            | block_item_list block_item
        """
        # Empty block items (plain ';') produce [None], so ignore them
        p[0] = p[1] if (len(p) == 2 or p[2] == [None]) else p[1] + p[2]
    
    def p_compound_statement_1(self, p):
        """ compound_statement : brace_open block_item_list_opt brace_close """
        p[0] = c_ast.Compound(
            block_items=p[2], 
            coord=self._coord(p.lineno(1)))
    
    def p_labeled_statement_1(self, p):
        """ labeled_statement : ID COLON statement """
        p[0] = c_ast.Label(p[1], p[3], self._coord(p.lineno(1)))
    
    def p_labeled_statement_2(self, p):
        """ labeled_statement : CASE constant_expression COLON statement """
        p[0] = c_ast.Case(p[2], [p[4]], self._coord(p.lineno(1)))
        
    def p_labeled_statement_3(self, p):
        """ labeled_statement : DEFAULT COLON statement """
        p[0] = c_ast.Default([p[3]], self._coord(p.lineno(1)))
        
    def p_selection_statement_1(self, p):
        """ selection_statement : IF LPAREN expression RPAREN statement """
        p[0] = c_ast.If(p[3], p[5], None, self._coord(p.lineno(1)))
    
    def p_selection_statement_2(self, p):
        """ selection_statement : IF LPAREN expression RPAREN statement ELSE statement """
        p[0] = c_ast.If(p[3], p[5], p[7], self._coord(p.lineno(1)))
    
    def p_selection_statement_3(self, p):
        """ selection_statement : SWITCH LPAREN expression RPAREN statement """
        p[0] = fix_switch_cases(
                c_ast.Switch(p[3], p[5], self._coord(p.lineno(1))))
    
    def p_iteration_statement_1(self, p):
        """ iteration_statement : WHILE LPAREN expression RPAREN statement """
        p[0] = c_ast.While(p[3], p[5], self._coord(p.lineno(1)))
    
    def p_iteration_statement_2(self, p):
        """ iteration_statement : DO statement WHILE LPAREN expression RPAREN SEMI """
        p[0] = c_ast.DoWhile(p[5], p[2], self._coord(p.lineno(1)))
    
    def p_iteration_statement_3(self, p):
        """ iteration_statement : FOR LPAREN expression_opt SEMI expression_opt SEMI expression_opt RPAREN statement """
        p[0] = c_ast.For(p[3], p[5], p[7], p[9], self._coord(p.lineno(1)))
    
    def p_iteration_statement_4(self, p):
        """ iteration_statement : FOR LPAREN declaration expression_opt SEMI expression_opt RPAREN statement """
        p[0] = c_ast.For(c_ast.DeclList(p[3]), p[4], p[6], p[8], self._coord(p.lineno(1)))

    def p_jump_statement_1(self, p):
        """ jump_statement  : GOTO ID SEMI """
        p[0] = c_ast.Goto(p[2], self._coord(p.lineno(1)))
    
    def p_jump_statement_2(self, p):
        """ jump_statement  : BREAK SEMI """
        p[0] = c_ast.Break(self._coord(p.lineno(1)))
    
    def p_jump_statement_3(self, p):
        """ jump_statement  : CONTINUE SEMI """
        p[0] = c_ast.Continue(self._coord(p.lineno(1)))
        
    def p_jump_statement_4(self, p):
        """ jump_statement  : RETURN expression SEMI  
                            | RETURN SEMI 
        """
        p[0] = c_ast.Return(p[2] if len(p) == 4 else None, self._coord(p.lineno(1)))
    
    def p_expression_statement(self, p):
        """ expression_statement : expression_opt SEMI """
        if p[1] is None:
            p[0] = c_ast.EmptyStatement(self._coord(p.lineno(1)))
        else:
            p[0] = p[1]
    
    def p_expression(self, p):
        """ expression  : assignment_expression 
                        | expression COMMA assignment_expression
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            if not isinstance(p[1], c_ast.ExprList):
                p[1] = c_ast.ExprList([p[1]], p[1].coord)
            
            p[1].exprs.append(p[3])
            p[0] = p[1] 

    def p_typedef_name(self, p):
        """ typedef_name : TYPEID """
        p[0] = c_ast.IdentifierType([p[1]], coord=self._coord(p.lineno(1)))

    def p_assignment_expression(self, p):
        """ assignment_expression   : conditional_expression
                                    | unary_expression assignment_operator assignment_expression
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = c_ast.Assignment(p[2], p[1], p[3], p[1].coord)

    # K&R2 defines these as many separate rules, to encode 
    # precedence and associativity. Why work hard ? I'll just use
    # the built in precedence/associativity specification feature
    # of PLY. (see precedence declaration above)
    #
    def p_assignment_operator(self, p):
        """ assignment_operator : EQUALS
                                | XOREQUAL   
                                | TIMESEQUAL  
                                | DIVEQUAL    
                                | MODEQUAL    
                                | PLUSEQUAL   
                                | MINUSEQUAL  
                                | LSHIFTEQUAL 
                                | RSHIFTEQUAL 
                                | ANDEQUAL    
                                | OREQUAL     
        """
        p[0] = p[1]
        
    def p_constant_expression(self, p):
        """ constant_expression : conditional_expression """
        p[0] = p[1]
    
    def p_conditional_expression(self, p):
        """ conditional_expression  : binary_expression
                                    | binary_expression CONDOP expression COLON conditional_expression
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = c_ast.TernaryOp(p[1], p[3], p[5], p[1].coord)
    
    def p_binary_expression(self, p):
        """ binary_expression   : cast_expression
                                | binary_expression TIMES binary_expression
                                | binary_expression DIVIDE binary_expression
                                | binary_expression MOD binary_expression
                                | binary_expression PLUS binary_expression
                                | binary_expression MINUS binary_expression
                                | binary_expression RSHIFT binary_expression
                                | binary_expression LSHIFT binary_expression
                                | binary_expression LT binary_expression
                                | binary_expression LE binary_expression
                                | binary_expression GE binary_expression
                                | binary_expression GT binary_expression
                                | binary_expression EQ binary_expression
                                | binary_expression NE binary_expression
                                | binary_expression AND binary_expression
                                | binary_expression OR binary_expression
                                | binary_expression XOR binary_expression
                                | binary_expression LAND binary_expression
                                | binary_expression LOR binary_expression
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = c_ast.BinaryOp(p[2], p[1], p[3], p[1].coord)
    
    def p_cast_expression_1(self, p):
        """ cast_expression : unary_expression """
        p[0] = p[1]
        
    def p_cast_expression_2(self, p):
        """ cast_expression : LPAREN type_name RPAREN cast_expression """
        p[0] = c_ast.Cast(p[2], p[4], self._coord(p.lineno(1)))
    
    def p_unary_expression_1(self, p):
        """ unary_expression    : postfix_expression """
        p[0] = p[1]
    
    def p_unary_expression_2(self, p):
        """ unary_expression    : PLUSPLUS unary_expression 
                                | MINUSMINUS unary_expression
                                | unary_operator cast_expression
        """
        p[0] = c_ast.UnaryOp(p[1], p[2], p[2].coord)
    
    def p_unary_expression_3(self, p):
        """ unary_expression    : SIZEOF unary_expression 
                                | SIZEOF LPAREN type_name RPAREN
        """
        p[0] = c_ast.UnaryOp(
            p[1], 
            p[2] if len(p) == 3 else p[3], 
            self._coord(p.lineno(1)))
    
    def p_unary_operator(self, p):
        """ unary_operator  : AND
                            | TIMES
                            | PLUS
                            | MINUS
                            | NOT
                            | LNOT
        """
        p[0] = p[1]
                                
    def p_postfix_expression_1(self, p):
        """ postfix_expression  : primary_expression """
        p[0] = p[1]
    
    def p_postfix_expression_2(self, p):
        """ postfix_expression  : postfix_expression LBRACKET expression RBRACKET """
        p[0] = c_ast.ArrayRef(p[1], p[3], p[1].coord)
    
    def p_postfix_expression_3(self, p):
        """ postfix_expression  : postfix_expression LPAREN argument_expression_list RPAREN
                                | postfix_expression LPAREN RPAREN
        """
        p[0] = c_ast.FuncCall(p[1], p[3] if len(p) == 5 else None, p[1].coord)
    
    def p_postfix_expression_4(self, p):
        """ postfix_expression  : postfix_expression PERIOD identifier
                                | postfix_expression ARROW identifier
        """
        p[0] = c_ast.StructRef(p[1], p[2], p[3], p[1].coord)

    def p_postfix_expression_5(self, p):
        """ postfix_expression  : postfix_expression PLUSPLUS 
                                | postfix_expression MINUSMINUS
        """
        p[0] = c_ast.UnaryOp('p' + p[2], p[1], p[1].coord)

    def p_postfix_expression_6(self, p):
        """ postfix_expression  : LPAREN type_name RPAREN brace_open initializer_list brace_close
                                | LPAREN type_name RPAREN brace_open initializer_list COMMA brace_close
        """
        p[0] = c_ast.CompoundLiteral(p[2], p[5])

    def p_primary_expression_1(self, p):
        """ primary_expression  : identifier """
        p[0] = p[1]
        
    def p_primary_expression_2(self, p):
        """ primary_expression  : constant """
        p[0] = p[1]
        
    def p_primary_expression_3(self, p):
        """ primary_expression  : unified_string_literal 
                                | unified_wstring_literal
        """
        p[0] = p[1]
            
    def p_primary_expression_4(self, p):
        """ primary_expression  : LPAREN expression RPAREN """
        p[0] = p[2]
        
    def p_argument_expression_list(self, p):
        """ argument_expression_list    : assignment_expression 
                                        | argument_expression_list COMMA assignment_expression
        """
        if len(p) == 2: # single expr
            p[0] = c_ast.ExprList([p[1]], p[1].coord)
        else:
            p[1].exprs.append(p[3])
            p[0] = p[1]
        
    def p_identifier(self, p):
        """ identifier  : ID """
        p[0] = c_ast.ID(p[1], self._coord(p.lineno(1)))
        
    def p_constant_1(self, p):
        """ constant    : INT_CONST_DEC
                        | INT_CONST_OCT
                        | INT_CONST_HEX
        """
        p[0] = c_ast.Constant(
            'int', p[1], self._coord(p.lineno(1)))
            
    def p_constant_2(self, p):
        """ constant    : FLOAT_CONST
                        | HEX_FLOAT_CONST
        """
        p[0] = c_ast.Constant(
            'float', p[1], self._coord(p.lineno(1)))
    
    def p_constant_3(self, p):
        """ constant    : CHAR_CONST
                        | WCHAR_CONST
        """
        p[0] = c_ast.Constant(
            'char', p[1], self._coord(p.lineno(1)))
    
    # The "unified" string and wstring literal rules are for supporting 
    # concatenation of adjacent string literals.
    # I.e. "hello " "world" is seen by the C compiler as a single string literal
    # with the value "hello world"
    #
    def p_unified_string_literal(self, p):
        """ unified_string_literal  : STRING_LITERAL
                                    | unified_string_literal STRING_LITERAL  
        """
        if len(p) == 2: # single literal
            p[0] = c_ast.Constant(
                'string', p[1], self._coord(p.lineno(1)))
        else:
            p[1].value = p[1].value[:-1] + p[2][1:]
            p[0] = p[1]
            
    def p_unified_wstring_literal(self, p):
        """ unified_wstring_literal : WSTRING_LITERAL
                                    | unified_wstring_literal WSTRING_LITERAL  
        """
        if len(p) == 2: # single literal
            p[0] = c_ast.Constant(
                'string', p[1], self._coord(p.lineno(1)))
        else:
            p[1].value = p[1].value.rstrip[:-1] + p[2][1:]
            p[0] = p[1]

    def p_brace_open(self, p):
        """ brace_open  :   LBRACE
        """
        self._push_scope()
        p[0] = p[1]

    def p_brace_close(self, p):
        """ brace_close :   RBRACE
        """
        self._pop_scope()
        p[0] = p[1]

    def p_empty(self, p):
        'empty : '
        p[0] = None
        
    def p_error(self, p):
        if p:
            self._parse_error(
                'before: %s' % p.value, 
                self._coord(lineno=p.lineno,
                            column=self.clex.find_tok_column(p)))
        else:
            self._parse_error('At end of input', '')


#------------------------------------------------------------------------------
if __name__ == "__main__":
    import pprint
    import time, sys
    
    #t1 = time.time()
    #parser = CParser(lex_optimize=True, yacc_debug=True, yacc_optimize=False)
    #sys.write(time.time() - t1)
    
    #buf = ''' 
        #int (*k)(int);
    #'''
    
    ## set debuglevel to 2 for debugging
    #t = parser.parse(buf, 'x.c', debuglevel=0)
    #t.show(showcoord=True)

