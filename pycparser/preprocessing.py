import re

def code_preprocessing(file):
    
    comment_lines, raw_codeLines = comment_finder(file)
    comment_lines.reverse()
    for i in comment_lines:
        raw_codeLines.pop(i)
    for line_number in range(len(raw_codeLines)):
        placeHolder = raw_codeLines[line_number][1]
        placeHolder = space_out(placeHolder, ";")
        placeHolder = space_out(placeHolder, "(")
        placeHolder = space_out(placeHolder, ")")
        placeHolder = space_out(placeHolder, ",")
        raw_codeLines[line_number][1] = placeHolder

    return raw_codeLines, comment_lines.reverse()


def insert_space(string, index):
    string_copy = ""
    for i in range(len(string)):
        if i==(index):
            string_copy += " "
            string_copy += string[i]
            string_copy += " "
            continue
        string_copy += string[i]
    return string_copy

def find_char_indices(input_string, char):
    indices = []
    replacement_token = 0
    for index, character in enumerate(input_string):
        if character == char:
            indices.append(index + 2*replacement_token)
            replacement_token+=1
    return indices

def space_out(string, char):
    indices = find_char_indices(string, char)

    for i in indices:
        string = insert_space(string, i)
    return string


def comment_finder(file):
    with open(file) as dataset_obj:
        codeLines = dataset_obj.read()
        comment_lines = []
        raw_codeLines = codeLines.replace("\t","").split("\n")
        raw_codeLines = [[i, raw_codeLines[i]] for i in range(len(raw_codeLines))]
        multi_line_flag = 0
        for line_number in range(len(raw_codeLines)):
            if multi_line_flag:
                if raw_codeLines[line_number][1].__contains__("*/"):
                    multi_line_flag = 0
                comment_lines.append(line_number)
            elif raw_codeLines[line_number][1].__contains__("/*"):
                if raw_codeLines[line_number][1].lstrip(' ').startswith("/*") and not(raw_codeLines[line_number][1].__contains__("*/")):
                    comment_lines.append(line_number)
                    multi_line_flag = 1
                elif raw_codeLines[line_number][1].__contains__("/*") and not(raw_codeLines[line_number][1].lstrip(' ').startswith("/*")):
                    if raw_codeLines[line_number][1].__contains__("*/"):
                        psuedo_multi_line_start = raw_codeLines[line_number][1].find("/*")
                        psuedo_multi_line_end = raw_codeLines[line_number][1].find("*/")
                        temporary_line = raw_codeLines[line_number][1][:psuedo_multi_line_start] + raw_codeLines[line_number][1][psuedo_multi_line_end+2:]
                        raw_codeLines[line_number][1] = temporary_line
                elif raw_codeLines[line_number][1].__contains__("/*") and (raw_codeLines[line_number][1].lstrip(' ').startswith("/*")):
                    if raw_codeLines[line_number][1].__contains__("*/") and raw_codeLines[line_number][1].endswith("*/"):
                        comment_lines.append(line_number)

            elif raw_codeLines[line_number][1].lstrip(' ').startswith("//"):
                comment_lines.append(line_number)
            elif raw_codeLines[line_number][1].__contains__("//"):
                comment_start = raw_codeLines[line_number][1].find('//')
                raw_codeLines[line_number][1] = raw_codeLines[line_number][1][:comment_start]
    return comment_lines, raw_codeLines

def find_undefined_types_in_variables(code_list):

    cpp_keywords = [
    "alignas",
    "alignof",
    "and",
    "and_eq",
    "asm",
    "auto",
    "bitand",
    "bitor",
    "bool",
    "break",
    "case",
    "catch",
    "char",
    "char16_t",
    "char32_t",
    "class",
    "compl",
    "const",
    "constexpr",
    "const_cast",
    "continue",
    "decltype",
    "default",
    "delete",
    "do",
    "double",
    "dynamic_cast",
    "else",
    "enum",
    "explicit",
    "export",
    "extern",
    "false",
    "float",
    "for",
    "friend",
    "goto",
    "if",
    "inline",
    "int",
    "long",
    "mutable",
    "namespace",
    "new",
    "noexcept",
    "not",
    "not_eq",
    "nullptr",
    "operator",
    "or",
    "or_eq",
    "private",
    "protected",
    "public",
    "register",
    "reinterpret_cast",
    "return",
    "short",
    "signed",
    "sizeof",
    "static",
    "static_assert",
    "static_cast",
    "struct",
    "switch",
    "template",
    "this",
    "thread_local",
    "throw",
    "true",
    "try",
    "typedef",
    "typeid",
    "typename",
    "union",
    "unsigned",
    "using",
    "virtual",
    "void",
    "volatile",
    "wchar_t",
    "while",
    "xor",
    "xor_eq",
    "%d",
    "%f",
    "%s"
]

    defined_types = {'int', 'char', 'float', 'double', 'long', 'short', 'void'}
    undefined_types = set()

    variable_pattern = r'\b((?:[a-zA-Z_]\w*\**)\s+\**\s*\**[a-zA-Z_]\w*\[*\w*\]*)\s*(?:,|\s*;|\s*=|\s*\))'

    for line in enumerate(code_list):
        variable_matches = re.findall(variable_pattern, line[1][1])
        for variable_declaration in variable_matches:
            data_type = variable_declaration.split()[0]
            if data_type == 'd':
                pass
            elif (data_type not in defined_types) and (data_type not in cpp_keywords):
                undefined_types.add(data_type)
                code_list[line[0]][1] = (line[1][1].replace((variable_declaration.split()[0]+ ' '), 'int '))

    return list(undefined_types), code_list


def find_undefined_function_types(code_list):

    defined_types = set(['int', 'char', 'float', 'double', 'long', 'short', 'void'])
    undefined_types = set()
    
    function_pattern = r'\b([a-zA-Z_]\w*\s*\**)\s+\w+\s*\([^)]*\)\s*{'
    
    temp_list = [i[1] for i in code_list]
    lines = "\n".join(temp_list)
    temp = lines

    function_matches = re.findall(function_pattern, lines)
    
    for return_type in function_matches:
        if return_type.strip('*') not in defined_types:
            undefined_types.add(return_type.strip('*'))

            temp = (temp.replace(return_type, 'int'))

    
    return list(undefined_types), temp