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
