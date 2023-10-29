"""
Configuration for docs
"""
from frappe import _
# source_link = "https://github.com/[org_name]/agriculture"
# headline = "App that does everything"
# sub_heading = "Yes, you got that right the first time, everything"

def get_context(context):
	context.brand_html = _("Agriculture Management")
