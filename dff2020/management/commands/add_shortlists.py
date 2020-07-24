from django.core.management.base import BaseCommand
from django.db import transaction
from dff2020.models import Shortlist, Question, Option

import logging
import json
import os

logger = logging.getLogger("app.dff2020.commands")


class Command(BaseCommand):
    help = "loading questions from json file"

    def add_arguments(self, parser):
        parser.add_argument("filename", type=str)

    def handle(self, *args, **options):
        filename = options["filename"]
        if not os.path.exists(filename):
            logger.info("No such file")
            return
        try:
            shortlists = json.loads(open(filename, "r").read())
        except Exception as ex:
            logger.debug(f"Error parsing {filename}")
            logger.exception(ex)
        else:
            with transaction.atomic():
                self.insert_shortlists(shortlists)

    def insert_shortlists(self, shortlists):
        for shortlist in shortlists:
            questions = shortlist.pop("questions")
            shortlist = Shortlist.objects.create(**shortlist)
            self.insert_questions(shortlist.id, questions)

    def insert_questions(self, shortlist_id, questions):
        for question in questions:
            options = question.pop("options")
            question = Question.objects.create(shortlist_id=shortlist_id, **question)
            self.insert_options(question.id, options)

    def insert_options(self, question_id, options):
        for option in options:
            Option.objects.create(question_id=question_id, **option)

