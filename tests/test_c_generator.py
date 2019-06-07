import sys
import textwrap
import unittest

# Run from the root dir
sys.path.insert(0, '.')

from pycparser import c_parser, c_generator, c_ast, parse_file

_c_parser = c_parser.CParser(
                lex_optimize=False,
                yacc_debug=True,
                yacc_optimize=False,
                yacctab='yacctab')


def compare_asts(ast1, ast2):
    if type(ast1) != type(ast2):
        return False
    if isinstance(ast1, tuple) and isinstance(ast2, tuple):
        if ast1[0] != ast2[0]:
            return False
        ast1 = ast1[1]
        ast2 = ast2[1]
        return compare_asts(ast1, ast2)
    for attr in ast1.attr_names:
        if getattr(ast1, attr) != getattr(ast2, attr):
            return False
    for i, c1 in enumerate(ast1.children()):
        if compare_asts(c1, ast2.children()[i]) == False:
            return False
    return True


def parse_to_ast(src):
    return _c_parser.parse(src)


class TestFunctionDeclGeneration(unittest.TestCase):
    class _FuncDeclVisitor(c_ast.NodeVisitor):
        def __init__(self):
            self.stubs = []

        def visit_FuncDecl(self, node):
            gen = c_generator.CGenerator()
            self.stubs.append(gen.visit(node))

    def test_partial_funcdecl_generation(self):
        src = r'''
            void noop(void);
            void *something(void *thing);
            int add(int x, int y);'''
        ast = parse_to_ast(src)
        v = TestFunctionDeclGeneration._FuncDeclVisitor()
        v.visit(ast)
        self.assertEqual(len(v.stubs), 3)
        self.assertTrue(r'void noop(void)' in v.stubs)
        self.assertTrue(r'void *something(void *thing)' in v.stubs)
        self.assertTrue(r'int add(int x, int y)' in v.stubs)


class TestCtoC(unittest.TestCase):
    def _run_c_to_c(self, src):
        ast = parse_to_ast(src)
        generator = c_generator.CGenerator()
        return generator.visit(ast)

    def _assert_ctoc_correct(self, src):
        """ Checks that the c2c translation was correct by parsing the code
            generated by c2c for src and comparing the AST with the original
            AST.
        """
        src2 = self._run_c_to_c(src)
        self.assertTrue(compare_asts(parse_to_ast(src), parse_to_ast(src2)),
                        src2)

    def test_trivial_decls(self):
        self._assert_ctoc_correct('int a;')
        self._assert_ctoc_correct('int b, a;')
        self._assert_ctoc_correct('int c, b, a;')

    def test_complex_decls(self):
        self._assert_ctoc_correct('int** (*a)(void);')
        self._assert_ctoc_correct('int** (*a)(void*, int);')
        self._assert_ctoc_correct('int (*b)(char * restrict k, float);')
        self._assert_ctoc_correct('int test(const char* const* arg);')
        self._assert_ctoc_correct('int test(const char** const arg);')

        #s = 'int test(const char* const* arg);'
        #parse_to_ast(s).show()

    def test_ternary(self):
        self._assert_ctoc_correct('''
            int main(void)
            {
                int a, b;
                (a == 0) ? (b = 1) : (b = 2);
            }''')

    def test_casts(self):
        self._assert_ctoc_correct(r'''
            int main() {
                int b = (int) f;
                int c = (int*) f;
            }''')
        self._assert_ctoc_correct(r'''
            int main() {
                int a = (int) b + 8;
                int t = (int) c;
            }
        ''')

    def test_initlist(self):
        self._assert_ctoc_correct('int arr[] = {1, 2, 3};')

    def test_exprs(self):
        self._assert_ctoc_correct('''
            int main(void)
            {
                int a;
                int b = a++;
                int c = ++a;
                int d = a--;
                int e = --a;
            }''')

    def test_statements(self):
        # note two minuses here
        self._assert_ctoc_correct(r'''
            int main() {
                int a;
                a = 5;
                ;
                b = - - a;
                return a;
            }''')

    def test_struct_decl(self):
        self._assert_ctoc_correct(r'''
            typedef struct node_t {
                struct node_t* next;
                int data;
            } node;
            ''')

    def test_krstyle(self):
        self._assert_ctoc_correct(r'''
            int main(argc, argv)
            int argc;
            char** argv;
            {
                return 0;
            }
        ''')

    def test_switchcase(self):
        self._assert_ctoc_correct(r'''
        int main() {
            switch (myvar) {
            case 10:
            {
                k = 10;
                p = k + 1;
                break;
            }
            case 20:
            case 30:
                return 20;
            default:
                break;
            }
        }
        ''')

    def test_nest_initializer_list(self):
        self._assert_ctoc_correct(r'''
        int main()
        {
           int i[1][1] = { { 1 } };
        }''')

    def test_nest_named_initializer(self):
        self._assert_ctoc_correct(r'''struct test
            {
                int i;
                struct test_i_t
                {
                    int k;
                } test_i;
                int j;
            };
            struct test test_var = {.i = 0, .test_i = {.k = 1}, .j = 2};
        ''')

    def test_expr_list_in_initializer_list(self):
        self._assert_ctoc_correct(r'''
        int main()
        {
           int i[1] = { (1, 2) };
        }''')

    def test_issue36(self):
        self._assert_ctoc_correct(r'''
            int main() {
            }''')

    def test_issue37(self):
        self._assert_ctoc_correct(r'''
            int main(void)
            {
              unsigned size;
              size = sizeof(size);
              return 0;
            }''')

    def test_issue66(self):
        # A non-existing body must not be generated
        # (previous valid behavior, still working)
        self._assert_ctoc_correct(r'''
            struct foo;
            ''')
        # An empty body must be generated
        # (added behavior)
        self._assert_ctoc_correct(r'''
            struct foo {};
            ''')

    def test_issue83(self):
        self._assert_ctoc_correct(r'''
            void x(void) {
                int i = (9, k);
            }
            ''')

    def test_issue84(self):
        self._assert_ctoc_correct(r'''
            void x(void) {
                for (int i = 0;;)
                    i;
            }
            ''')

    def test_issue246(self):
        self._assert_ctoc_correct(r'''
            int array[3] = {[0] = 0, [1] = 1, [1+1] = 2};
            ''')

    def test_exprlist_with_semi(self):
        self._assert_ctoc_correct(r'''
            void x() {
                if (i < j)
                    tmp = C[i], C[i] = C[j], C[j] = tmp;
                if (i <= j)
                    i++, j--;
            }
        ''')

    def test_exprlist_with_subexprlist(self):
        self._assert_ctoc_correct(r'''
            void x() {
                (a = b, (b = c, c = a));
            }
        ''')

    def test_comma_operator_funcarg(self):
        self._assert_ctoc_correct(r'''
            void f(int x) { return x; }
            int main(void) { f((1, 2)); return 0; }
        ''')

    def test_comma_op_in_ternary(self):
        self._assert_ctoc_correct(r'''
            void f() {
                (0, 0) ? (0, 0) : (0, 0);
            }
        ''')

    def test_comma_op_assignment(self):
        self._assert_ctoc_correct(r'''
            void f() {
                i = (a, b, c);
            }
        ''')

    def test_pragma(self):
        self._assert_ctoc_correct(r'''
            #pragma foo
            void f() {
                #pragma bar
                i = (a, b, c);
            }
            typedef struct s {
            #pragma baz
           } s;
        ''')

    def test_compound_literal(self):
        self._assert_ctoc_correct('char **foo = (char *[]){ "x", "y", "z" };')
        self._assert_ctoc_correct('int i = ++(int){ 1 };')
        self._assert_ctoc_correct('struct foo_s foo = (struct foo_s){ 1, 2 };')

    def test_enum(self):
        self._assert_ctoc_correct(r'''
            enum e
            {
              a,
              b = 2,
              c = 3
            };
        ''')
        self._assert_ctoc_correct(r'''
            enum f
            {
                g = 4,
                h,
                i
            };
        ''')

    def test_enum_typedef(self):
        self._assert_ctoc_correct('typedef enum EnumName EnumTypedefName;')

    def test_generate_struct_union_enum_exception(self):
        generator = c_generator.CGenerator()
        self.assertRaises(
            AssertionError,
            generator._generate_struct_union_enum,
            n=c_ast.Struct(
                name='TestStruct',
                decls=[],
            ),
            name='',
        )

    def test_array_decl(self):
        self._assert_ctoc_correct('int g(const int a[const 20]){}')
        ast = parse_to_ast('const int a[const 20];')
        generator = c_generator.CGenerator()
        self.assertEqual(generator.visit(ast.ext[0].type),
                         'const int [const 20]')
        self.assertEqual(generator.visit(ast.ext[0].type.type),
                         'const int')

    def test_ptr_decl(self):
        src = 'const int ** const  x;'
        self._assert_ctoc_correct(src)
        ast = parse_to_ast(src)
        generator = c_generator.CGenerator()
        self.assertEqual(generator.visit(ast.ext[0].type),
                         'const int ** const')
        self.assertEqual(generator.visit(ast.ext[0].type.type),
                         'const int *')
        self.assertEqual(generator.visit(ast.ext[0].type.type.type),
                         'const int')


class TestCasttoC(unittest.TestCase):
    def test_to_type(self):
        src = 'int *x;'
        generator = c_generator.CGenerator()
        test_fun = c_ast.FuncCall(c_ast.ID('test_fun'), c_ast.ExprList([]))

        ast1 = parse_to_ast(src)
        int_ptr_type = ast1.ext[0].type
        int_type = int_ptr_type.type
        self.assertEqual(generator.visit(c_ast.Cast(int_ptr_type, test_fun)),
                         '(int *) test_fun()')
        self.assertEqual(generator.visit(c_ast.Cast(int_type, test_fun)),
                         '(int) test_fun()')

        ast2 = parse_file('examples/c_files/memmgr.h', use_cpp=True)
        void_ptr_type = ast2.ext[-3].type.type
        void_type = void_ptr_type.type
        self.assertEqual(generator.visit(c_ast.Cast(void_ptr_type, test_fun)),
                         '(void *) test_fun()')
        self.assertEqual(generator.visit(c_ast.Cast(void_type, test_fun)),
                         '(void) test_fun()')

if __name__ == "__main__":
    unittest.main()
