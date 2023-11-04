app_name = "agriculture_management"
app_title = "Agriculture Management"
app_publisher = "aminos"
app_description = "Agriculture Management System"
app_email = "hamdiahmedamin@gmail.com"
app_license = "mit"
app_include_icons ="agriculture_management/icons.html"

required_apps = ["erpnext"]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/agriculture_management/css/agriculture_management.css"
# app_include_js = "/assets/agriculture_management/js/agriculture_management.js"

# include js, css files in header of web template
# web_include_css = "/assets/agriculture_management/css/agriculture_management.css"
# web_include_js = "/assets/agriculture_management/js/agriculture_management.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "agriculture_management/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "agriculture_management/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "agriculture_management.utils.jinja_methods",
#	"filters": "agriculture_management.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "agriculture_management.install.before_install"
after_install = "agriculture_management.install.after_install"
after_sync = "agriculture_management.install.after_sync"

# Uninstallation
# ------------

before_uninstall = "agriculture_management.uninstall.before_uninstall"
# after_uninstall = "agriculture_management.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "agriculture_management.utils.before_app_install"
# after_app_install = "agriculture_management.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "agriculture_management.utils.before_app_uninstall"
# after_app_uninstall = "agriculture_management.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "agriculture_management.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
#	"*": {
#		"on_update": "method",
#		"on_cancel": "method",
#		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
#	"all": [
#		"agriculture_management.tasks.all"
#	],
#	"daily": [
#		"agriculture_management.tasks.daily"
#	],
#	"hourly": [
#		"agriculture_management.tasks.hourly"
#	],
#	"weekly": [
#		"agriculture_management.tasks.weekly"
#	],
#	"monthly": [
#		"agriculture_management.tasks.monthly"
#	],
# }

# Testing
# -------

# before_tests = "agriculture_management.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "agriculture_management.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "agriculture_management.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["agriculture_management.utils.before_request"]
# after_request = ["agriculture_management.utils.after_request"]

# Job Events
# ----------
# before_job = ["agriculture_management.utils.before_job"]
# after_job = ["agriculture_management.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"agriculture_management.auth.validate"
# ]

global_search_doctypes = {
	"Agriculture Management": [
		{'doctype': 'Weather', 'index': 1},
		{'doctype': 'Soil Texture', 'index': 2},
		{'doctype': 'Water Analysis', 'index': 3},
		{'doctype': 'Soil Analysis', 'index': 4},
		{'doctype': 'Plant Analysis', 'index': 5},
		{'doctype': 'Agriculture Analysis Criteria', 'index': 6},
		{'doctype': 'Disease', 'index': 7},
		{'doctype': 'Crop', 'index': 8},
		{'doctype': 'Fertilizer', 'index': 9},
		{'doctype': 'Crop Cycle', 'index': 10}
	]
}
