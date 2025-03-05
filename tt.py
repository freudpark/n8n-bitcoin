import tabulate

data = [["사과", 1000], ["배", 1500], ["딸기", 3000]]
headers = ["품목", "가격"]

table = tabulate.tabulate(data, headers=headers)
print(table)