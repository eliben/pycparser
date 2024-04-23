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
