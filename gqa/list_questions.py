
from .questions import question_forms

if __name__ == "__main__":

	print("Questions:")

	for i in question_forms:
		print(i.english_explain())

	print("\nTypes:")

	for i in question_forms:
		print(i.type_string, '-', i.group) 