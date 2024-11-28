import os, yara_x

def runRulesAgainst(file):
    compiler = yara_x.Compiler()
    compiler.new_namespace("ScrutinPunchor")
    compiler.add_source('rule detectBombeWord { strings: $word="bombe" nocase condition: $word }')
    rules = compiler.build()
    scanner = yara_x.Scanner(rules)
    print(len(scanner.scan_file(file).matching_rules))

while True:
    path = r"G:\folder1"
    if os.path.isdir(path):
        break

for walker in os.walk(path):
    root_folder = walker[0]
    for file in walker[-1]:
        runRulesAgainst(f"{root_folder}{os.path.sep}{file}")
