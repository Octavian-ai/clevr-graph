

import os
import yaml
import random
import uuid
import sys
import traceback
from tqdm import tqdm
from collections import Counter

from .questions import question_forms
from .generate_graph import GraphGenerator
from .types import *
from .args import *

import logging
logger = logging.getLogger(__name__)

if __name__ == "__main__":

	args = get_args()

	logging.basicConfig()
	logger.setLevel(args.log_level)
	logging.getLogger('gqa').setLevel(args.log_level)

	filename = f"./data/gqa-{uuid.uuid4()}.yaml"
	logger.info(f"Generating {args.count} (G,Q,A) tuples into {filename}")

	os.makedirs("./data", exist_ok=True)

	def type_matches(tpe):
		
		if args.type_string_prefix is None:
			return True

		for i in args.type_string_prefix:
			if tpe.startswith(i):
				return True

		return False


	with open(filename, "w") as file:

		f_try = Counter()
		f_success = Counter()

		def forms():
			while True:
				for form in question_forms:
					yield form

		def specs():
			form_gen = forms()
			i = 0
			fail = 0
			with tqdm(total=args.count) as pbar:
				while i < args.count:

					try:
						g = GraphGenerator(args).generate().graph_spec
						logger.debug("Generated graph")

						if len(g.nodes) == 0 or len(g.edges) == 0:
							raise ValueError("Empty graph was generated")


						j = 0
						while j < args.questions_per_graph:
							form = next(form_gen)

							if type_matches(form.type_string):

								f_try[form.type_string] += 1
								
								logger.debug(f"Generating question '{form.english}'")
								q, a = form.generate(g)

								f_success[form.type_string] += 1
								i += 1
								j += 1
								pbar.update(1)

								logger.debug(f"Question: '{q}', answer: '{a}'")

								if args.omit_graph:
									yield DocumentSpec(None,q,a).stripped()
								else:
									yield DocumentSpec(g,q,a).stripped()
							
					except Exception as ex:
						logger.debug(f"Exception {ex} whilst trying to generate GQA")
						fail += 1
						if fail >= args.count / 3:
							raise Exception(f"Too many exceptions whilst trying to generate GQA e.g. {ex}")
						

		yaml.dump_all(specs(), file, explicit_start=True)

		logger.info(f"GQA per question type: {f_success}")

		for i in f_try:
			if i in f_success: 
				if f_success[i] < f_try[i]:
					logger.warn(f"Question form {i} failed to generate {f_try[i] - f_success[i]}/{f_try[i]}")
			else:
				logger.warn(f"Question form {i} totally failed to generate")

				



