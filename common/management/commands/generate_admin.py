"""
Usage
python manage.py generate_admin {app} > {app}/admin.py
"""
import datetime
import os
import re
import sys
import six
from django.db import models
from django.core.management.base import BaseCommand, CommandError
from django.db.models import ManyToManyField, ManyToOneRel
from django.apps.registry import apps


# region Command setup


def get_models(app):
    for model in app.get_models():
        yield model


def get_apps():
    for app_config in apps.get_app_configs():
        yield app_config.name, app_config


def get_all_fields(model, include_str=True, ignore=None):
    all_fields = [
        field.name
        for field in model._meta.get_fields()
        if not isinstance(
            field,
            (
                ManyToOneRel,
                ManyToManyField,
            ),
        )
    ]

    if type(ignore) == list and ignore:
        all_fields = [field_name for field_name in all_fields if field_name not in ignore]
    return ["__str__"] + all_fields if include_str else all_fields


# region Variables

MAX_LINE_WIDTH = 78
INDENT_WIDTH = 4

LIST_FILTER = (
    models.DateField,
    models.DateTimeField,
    models.ForeignKey,
    models.BooleanField,
)

SEARCH_FIELD_NAMES = (
    "name",
    "slug",
    "value",
)

DATE_HIERARCHY_NAMES = (
    "created",
    "modified",
)

PREPOPULATED_FIELD_NAMES = ("slug=name",)

DATE_HIERARCHY_THRESHOLD = 250
LIST_FILTER_THRESHOLD = 25
RAW_ID_THRESHOLD = 100
NO_QUERY_DB = True

PRINT_IMPORTS = """
from django.contrib import admin
from import_export.admin import ImportExportMixin
from import_export import resources
from . import models

"""

PRINT_ADMIN_CLASS = """

@admin.register(models.%(name)s)
class %(name)sAdmin(ImportExportMixin, admin.ModelAdmin):

    class %(name)sResource(resources.ModelResource):
        class Meta:
            model = models.%(name)s
%(class_)s
"""


PRINT_ADMIN_PROPERTY = """
    %(key)s = %(value)s"""

# endregion


def cprint(*args, **kwargs):
    print('"""')
    print(*args, **kwargs)
    print('"""')


class AdminApp(object):
    def __init__(self, app, model_res, **options):
        self.app = app
        self.model_res = model_res
        self.options = options

    def __iter__(self):
        for model in get_models(self.app):
            admin_model = AdminModel(model, **self.options)

            for model_re in self.model_res:
                if model_re.search(admin_model.name):
                    break
            else:
                if self.model_res:
                    continue

            yield admin_model

    def __unicode__(self):
        return six.u("").join(self._unicode_generator())

    def __str__(self):  # pragma: no cover
        if six.PY2:
            return six.text_type(self).encode("utf-8", "replace")
        else:
            return self.__unicode__()

    def _unicode_generator(self):
        yield PRINT_IMPORTS

        admin_model_names = []

        # calls the __iter__ method
        for admin_model in self:
            yield PRINT_ADMIN_CLASS % dict(
                name=admin_model.name,
                class_=admin_model,
            )
            admin_model_names.append(admin_model.name)

    def __repr__(self):
        return "<%s[%s]>" % (
            self.__class__.__name__,
            self.app,
        )


class AdminModel(object):
    PRINTABLE_PROPERTIES = (
        "list_display",
        "list_filter",
        "raw_id_fields",
        "search_fields",
        "prepopulated_fields",
        "date_hierarchy",
    )

    def __init__(
        self,
        model,
        raw_id_threshold=RAW_ID_THRESHOLD,
        date_hierarchy_threshold=DATE_HIERARCHY_THRESHOLD,
        list_filter_threshold=LIST_FILTER_THRESHOLD,
        search_field_names=SEARCH_FIELD_NAMES,
        date_hierarchy_names=DATE_HIERARCHY_NAMES,
        prepopulated_field_names=PREPOPULATED_FIELD_NAMES,
        no_query_db=NO_QUERY_DB,
        **options,
    ):
        self.model = model
        self.list_display = []
        self.list_filter = []
        self.raw_id_fields = []
        self.search_fields = []
        self.prepopulated_fields = {}
        self.date_hierarchy = None
        self.search_field_names = search_field_names
        self.raw_id_threshold = raw_id_threshold
        self.list_filter_threshold = list_filter_threshold
        self.date_hierarchy_threshold = date_hierarchy_threshold
        self.date_hierarchy_names = date_hierarchy_names
        self.prepopulated_field_names = prepopulated_field_names
        self.query_db = not no_query_db

    def __repr__(self):
        return "<%s[%s]>" % (
            self.__class__.__name__,
            self.name,
        )

    @property
    def name(self):
        return self.model.__name__

    def _process_many_to_many(self, meta):
        raw_id_threshold = self.raw_id_threshold
        for field in meta.local_many_to_many:
            related_model = self._get_related_model(field)
            related_objects = related_model.objects.all()
            if related_objects[:raw_id_threshold].count() < raw_id_threshold:
                yield field.name

    def _process_fields(self, meta):
        parent_fields = meta.parents.values()
        for field in meta.fields:
            name = self._process_field(field, parent_fields)
            if name:  # pragma: no cover
                yield name

    @classmethod
    def _get_related_model(cls, field):  # pragma: no cover
        if hasattr(field, "remote_field"):
            related_model = field.remote_field.model
        elif hasattr(field.related, "related_model"):
            related_model = field.related.related_model
        else:
            related_model = field.related.model

        return related_model

    def _process_foreign_key(self, field):
        raw_id_threshold = self.raw_id_threshold
        list_filter_threshold = self.list_filter_threshold
        max_count = max(list_filter_threshold, raw_id_threshold)
        related_model = self._get_related_model(field)
        related_count = related_model.objects.all()
        related_count = related_count[:max_count].count()

        if related_count >= raw_id_threshold:
            self.raw_id_fields.append(field.name)

        elif related_count < list_filter_threshold:
            self.list_filter.append(field.name)

        else:  # pragma: no cover
            pass  # Do nothing :)

    def _process_field(self, field, parent_fields):
        if field in parent_fields:  # pragma: no cover
            return

        self.list_display.append(field.name)
        if isinstance(field, LIST_FILTER):
            if isinstance(field, models.ForeignKey) and self.query_db:
                self._process_foreign_key(field)
            else:
                self.list_filter.append(field.name)

        if field.name in self.search_field_names:
            self.search_fields.append(field.name)

        return field.name

    def __str__(self):  # pragma: no cover
        if six.PY2:
            return six.text_type(self).encode("utf-8", "replace")
        else:
            return self.__unicode__()

    def __unicode__(self):
        return six.u("").join(self._unicode_generator())

    def _yield_value(self, key, value):
        if isinstance(value, (list, set, tuple)):
            return self._yield_tuple(key, tuple(value))
        elif isinstance(value, dict):
            return self._yield_dict(key, value)
        elif isinstance(value, six.string_types):
            return self._yield_string(key, value)
        else:  # pragma: no cover
            raise TypeError("%s is not supported in %r" % (type(value), value))

    def _yield_string(self, key, value, converter=repr):
        return PRINT_ADMIN_PROPERTY % dict(
            key=key,
            value=converter(value),
        )

    def _yield_dict(self, key, value):
        row_parts = []
        row = self._yield_string(key, value)
        if len(row) > MAX_LINE_WIDTH:
            row_parts.append(self._yield_string(key, "{", str))
            for k, v in six.iteritems(value):
                row_parts.append("%s%r: %r" % (2 * INDENT_WIDTH * " ", k, v))

            row_parts.append(INDENT_WIDTH * " " + "}")
            row = six.u("\n").join(row_parts)

        return row

    def _yield_tuple(self, key, value):
        row_parts = []
        row = self._yield_string(key, value)
        if len(row) > MAX_LINE_WIDTH:
            row_parts.append(self._yield_string(key, "(", str))
            for v in value:
                row_parts.append(2 * INDENT_WIDTH * " " + repr(v) + ",")

            row_parts.append(INDENT_WIDTH * " " + ")")
            row = six.u("\n").join(row_parts)

        return row

    def _unicode_generator(self):
        self._process()
        for key in self.PRINTABLE_PROPERTIES:
            value = getattr(self, key)
            if value:
                yield self._yield_value(key, value)

    def _process(self):
        meta = self.model._meta
        field_names = list(self._process_fields(meta))
        for field_name in self.date_hierarchy_names[::-1]:
            if field_name in field_names and not self.date_hierarchy:
                self.date_hierarchy = field_name
                break

        for k in sorted(self.prepopulated_field_names):
            k, vs = k.split("=", 1)
            vs = vs.split(",")
            if k in field_names:
                incomplete = False
                for v in vs:
                    if v not in field_names:
                        incomplete = True
                        break

                if not incomplete:
                    self.prepopulated_fields[k] = vs

        self.processed = True


# endregion


class Command(BaseCommand):
    help = """Generate a `admin.py` file for the given app (models)"""

    def add_arguments(self, parser):
        parser.add_argument(
            "-s",
            "--search-field",
            action="append",
            default=SEARCH_FIELD_NAMES,
            help="Fields named like this will be added to `search_fields`",
        )
        parser.add_argument(
            "-d",
            "--date-hierarchy",
            action="append",
            default=DATE_HIERARCHY_NAMES,
            help="A field named like this will be set as `date_hierarchy`",
        )
        parser.add_argument(
            "--date-hierarchy-threshold",
            type=int,
            default=DATE_HIERARCHY_THRESHOLD,
            metavar="DATE_HIERARCHY_THRESHOLD",
            help="If a model has less than DATE_HIERARCHY_THRESHOLD items " "it will be added to `date_hierarchy`",
        )
        parser.add_argument(
            "-p",
            "--prepopulated-fields",
            action="append",
            default=PREPOPULATED_FIELD_NAMES,
            help="These fields will be prepopulated by the other field."
            "The field names can be specified like `spam=eggA,eggB,eggC`",
        )
        parser.add_argument(
            "-l",
            "--list-filter-threshold",
            type=int,
            default=LIST_FILTER_THRESHOLD,
            metavar="LIST_FILTER_THRESHOLD",
            help="If a foreign key/field has less than LIST_FILTER_THRESHOLD "
            "items it will be added to `list_filter`",
        )
        parser.add_argument(
            "-r",
            "--raw-id-threshold",
            type=int,
            default=RAW_ID_THRESHOLD,
            metavar="RAW_ID_THRESHOLD",
            help="If a foreign key has more than RAW_ID_THRESHOLD items " "it will be added to `list_filter`",
        )
        parser.add_argument(
            "-n",
            "--no-query-db",
            action="store_true",
            dest="no_query_db",
            help="Don't query the database in order to decide whether "
            "fields/relationships are added to `list_filter`",
        )
        parser.add_argument("app", help="App to generate admin definitions for")
        parser.add_argument("models", nargs="*", help="Regular expressions to filter the models by")

    def warning(self, message):
        self.stderr.write(self.style.WARNING(message))

    def handle(self, app=None, *args, **kwargs):
        try:
            installed_apps = dict(get_apps())

            app = installed_apps.get(app)
            if not app:
                self.warning("This command requires an existing app name as " "argument")
                self.warning("Available apps:")
                for app in sorted(installed_apps):
                    self.warning("    %s" % app)
                sys.exit(1)

            model_res = []
            models = kwargs.get("models", [])
            for model in models:
                model_res.append(re.compile(model, re.IGNORECASE))

            self.handle_app(app, model_res, **kwargs)
        except Exception as e:
            self.stderr.write("Error: %s" % e)
            raise CommandError(e)

    def handle_app(self, app, model_res, **options):
        filename = f"{app.name}/admin.py"
        if not os.path.exists(filename):
            self.warning(f"File {filename} does not exist, skipping")
            return

        generated_marker = f"# Generated on {datetime.datetime.now()}"

        output = f"""
{generated_marker}
{AdminApp(app, model_res, **options).__str__()}
        """
        with open(filename, "w") as f:
            f.write(output)
            print(f"Updated {filename}")
