import gspread
from oauth2client.service_account import ServiceAccountCredentials
from jira import JIRA
from utils import get_jira, authenticate_gspread, create_or_get_worksheet, add_issue_to_worksheet, get_current_jalali_date
from val_lc import get_cell_value_from_val  # وارد کردن تابع
from datetime import datetime
from khayyam import JalaliDatetime  # برای ماه شمسی
from pathlib import Path

# تابع اصلی
def main():
    # گرفتن مقدار cell_value از val.py
    cell_value = get_cell_value_from_val()  # این خط تابع ولیدیشن را فراخوانی می‌کند

    if not cell_value:
        print("No valid cell_value found.")
        return

    # اتصال به Jira
    jira = get_jira()

    # لیست برای ذخیره issue keys و زمان آپدیت آن‌ها
    issue_keys_with_time = []

    # ترکیب ماه و سال برای استفاده در customfield_22304
    custom_month_field_value = get_current_jalali_date()

    # 1. به‌روزرسانی برای Issues تهران
    jql_query = f"issuekey IN ({cell_value}) AND (City ~ تهران)"
    print(f"JQL Query for Tehran: {jql_query}")

    issues = jira.search_issues(jql_query, maxResults=0)
    fields_to_update = {
        "customfield_22631": {"value": "No"},
        "customfield_22632": {"value": "No"},
        "customfield_18602": {"value": "No"},
        "customfield_11003": {"value": "E"},
        "customfield_10804": {"value": "Lead Collection"},
        "customfield_22304": {"value": custom_month_field_value},  # ماه شمسی پویا
        "customfield_14314": {"value": "Tehran Sales"},
        "customfield_11100": {"value": "Tehran"}
    }

    for issue in issues:
        issue.update(fields=fields_to_update)
        print(f"Issue {issue.key} updated successfully for Tehran.")

    # 2. به‌روزرسانی برای Issues اطراف تهران
    jql_query = f"issuekey IN ({cell_value}) AND (City ~ اسلامشهر OR City ~ ورامین OR City ~ 'رباط کریم' OR City ~ پاکدشت OR City ~ قرچک OR City ~ بومهن OR City ~ لواسان OR City ~ رودهن OR City ~ جاجرود OR City ~ پرند OR City ~ دماوند)"
    print(f"JQL Query for Atraf Tehran: {jql_query}")

    issues = jira.search_issues(jql_query, maxResults=0)
    fields_to_update = {
        "customfield_22631": {"value": "No"},
        "customfield_22632": {"value": "No"},
        "customfield_18602": {"value": "No"},
        "customfield_11003": {"value": "E"},
        "customfield_10804": {"value": "Lead Collection"},
        "customfield_22304": {"value": custom_month_field_value},  # ماه شمسی پویا
        "customfield_14314": {"value": "Tehran Sales"},
        "customfield_11100": {"value": "Other Cities"}
    }

    for issue in issues:
        issue.update(fields=fields_to_update)
        print(f"Issue {issue.key} updated successfully for Atraf Tehran.")

    # 3. به‌روزرسانی برای سایر Issues
    jql_query = f"issuekey IN ({cell_value}) AND (City !~ تهران AND City !~ اسلامشهر AND City !~ ورامین AND City !~ 'رباط کریم' AND City !~ پاکدشت AND City !~ قرچک AND City !~ بومهن AND City !~ لواسان AND City !~ رودهن AND City !~ جاجرود AND City !~ پرند AND City !~ دماوند)"
    print(f"JQL Query for Other Cities: {jql_query}")

    issues = jira.search_issues(jql_query, maxResults=0)
    fields_to_update = {
        "customfield_22631": {"value": "No"},
        "customfield_22632": {"value": "No"},
        "customfield_18602": {"value": "No"},
        "customfield_11003": {"value": "E"},
        "customfield_10804": {"value": "Lead Collection"},
        "customfield_22304": {"value": custom_month_field_value},  # ماه شمسی پویا
        "customfield_14314": {"value": "Other Cities Sales"},
        "customfield_11100": {"value": "Other Cities"}
    }

    for issue in issues:
        issue.update(fields=fields_to_update)
        print(f"Issue {issue.key} updated successfully for Other Cities.")

    # 4. ترنزیشن به 'LC Pool' برای Lead Collection Issues
    jql_query = f"issuekey IN ({cell_value}) AND status = 'Lead Collection'"
    print(f"JQL Query for Lead Collection Transition: {jql_query}")

    issues = jira.search_issues(jql_query, maxResults=0)
    transition_name = 'LC Pool'

    for issue in issues:
        transitions = jira.transitions(issue)
        transition_id = None

        for t in transitions:
            if t['name'].lower() == transition_name.lower():
                transition_id = t['id']
                break

        if transition_id:
            jira.transition_issue(issue, transition_id)
            print(f"Issue {issue.key} transitioned to {transition_name}.")
        else:
            print(f"No valid transition found for issue {issue.key}.")

    # 5. ترنزیشن به 'NVR Linked Issue'
    jql_query = f"issuekey IN ({cell_value})"
    print(f"JQL Query for NVR Linked Issue Transition: {jql_query}")

    issues = jira.search_issues(jql_query, maxResults=0)
    transition_name = 'NVR Linked Issue'

    for issue in issues:
        transitions = jira.transitions(issue)
        transition_id = None

        for t in transitions:
            if t['name'].lower() == transition_name.lower():
                transition_id = t['id']
                break

        if transition_id:
            jira.transition_issue(issue, transition_id)
            print(f"Issue {issue.key} transitioned to {transition_name}.")
            # ذخیره زمان ترنزیشن موفقیت‌آمیز
            update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            issue_keys_with_time.append((issue.key, update_time))
        else:
            print(f"No valid transition found for issue {issue.key}.")

    # اتصال به Google Sheets
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

    # تنظیم مسیر فایل JSON به صورت نسبی
    current_directory = Path(__file__).parent
    json_keyfile = current_directory / "json.json"

    client = authenticate_gspread(json_keyfile, scope)

    # ایجاد یا باز کردن spreadsheet اصلی
    try:
        spreadsheet = client.open('Monthly Update LPO')
        print(f"Spreadsheet 'Monthly Update LPO' already exists.")
    except gspread.exceptions.SpreadsheetNotFound:
        spreadsheet = client.create('Monthly Update LPO')
        print(f"Spreadsheet 'Monthly Update LPO' created.")

    # گرفتن ماه شمسی جاری
    current_month = JalaliDatetime.now().strftime('%B')

    # ایجاد یا باز کردن worksheet با عنوان Lead Collection {ماه جاری}
    lead_collection_worksheet_name = f"Lead Collection {current_month}"
    lead_collection_worksheet = create_or_get_worksheet(spreadsheet, lead_collection_worksheet_name)

    # افزودن اطلاعات issues به worksheet
    add_issue_to_worksheet(lead_collection_worksheet, issue_keys_with_time)

if __name__ == "__main__":
    main()

