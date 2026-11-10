"""Single source of truth for column metadata in Workforce Pulse.

Business meanings follow the IBM HR Analytics dataset documentation (Kaggle).
Decisions marked "Review" are settled with evidence in 02_data_preparation.
"""

TARGET = "Attrition"
ID_COL = "EmployeeNumber"

# Protected / sensitive attributes: never model features, kept for fairness auditing only.
PROTECTED = ["Age", "Gender", "MaritalStatus"]

# Ordinal survey-style scales documented by IBM.
ORDINAL_LABELS = {
    "Education": {1: "Below College", 2: "College", 3: "Bachelor", 4: "Master", 5: "Doctor"},
    "EnvironmentSatisfaction": {1: "Low", 2: "Medium", 3: "High", 4: "Very High"},
    "JobInvolvement": {1: "Low", 2: "Medium", 3: "High", 4: "Very High"},
    "JobSatisfaction": {1: "Low", 2: "Medium", 3: "High", 4: "Very High"},
    "RelationshipSatisfaction": {1: "Low", 2: "Medium", 3: "High", 4: "Very High"},
    "PerformanceRating": {1: "Low", 2: "Good", 3: "Excellent", 4: "Outstanding"},
    "WorkLifeBalance": {1: "Bad", 2: "Good", 3: "Better", 4: "Best"},
}

# column -> (business category, business meaning, initial decision, reason)
COLUMNS = {
    "Age": ("Workforce profile", "Employee age in years", "Audit only", "Protected attribute: excluded from model, used for EDA and fairness audit"),
    "Attrition": ("Target", "Whether the employee left (Yes/No)", "Target", "Prediction outcome, kept separate from features"),
    "BusinessTravel": ("Work conditions", "Travel frequency (Non-Travel / Rarely / Frequently)", "Retain", "Working-condition indicator"),
    "DailyRate": ("Compensation", "Daily rate (undocumented definition)", "Review", "Meaning undocumented; check relation to MonthlyIncome before using"),
    "Department": ("Organizational", "Department (HR / R&D / Sales)", "Retain", "Organizational structure"),
    "DistanceFromHome": ("Work conditions", "Distance from home to work (units undocumented)", "Retain", "Commute burden proxy"),
    "Education": ("Workforce profile", "Education level, 1=Below College .. 5=Doctor", "Retain", "Ordinal background attribute"),
    "EducationField": ("Workforce profile", "Field of study", "Retain", "Background attribute"),
    "EmployeeCount": ("Technical", "Record count per row", "Exclude", "Expected constant: carries no information"),
    "EmployeeNumber": ("Technical", "Employee identifier", "Key only", "Identifier: join/export key, never a feature"),
    "EnvironmentSatisfaction": ("Satisfaction", "Satisfaction with work environment, 1=Low .. 4=Very High", "Retain", "Employee experience"),
    "Gender": ("Workforce profile", "Gender (Male/Female)", "Audit only", "Protected attribute: excluded from model, used for fairness audit"),
    "HourlyRate": ("Compensation", "Hourly rate (undocumented definition)", "Review", "Meaning undocumented; check relation to MonthlyIncome before using"),
    "JobInvolvement": ("Satisfaction", "Job involvement, 1=Low .. 4=Very High", "Retain", "Engagement indicator"),
    "JobLevel": ("Organizational", "Job level 1..5", "Retain", "Seniority; check overlap with MonthlyIncome"),
    "JobRole": ("Organizational", "Job role", "Retain", "Organizational structure"),
    "JobSatisfaction": ("Satisfaction", "Job satisfaction, 1=Low .. 4=Very High", "Retain", "Employee experience"),
    "MaritalStatus": ("Workforce profile", "Marital status (Single/Married/Divorced)", "Audit only", "Protected attribute: excluded from model, used for fairness audit"),
    "MonthlyIncome": ("Compensation", "Monthly income", "Retain", "Primary compensation measure"),
    "MonthlyRate": ("Compensation", "Monthly rate (undocumented definition)", "Review", "Meaning undocumented; check relation to MonthlyIncome before using"),
    "NumCompaniesWorked": ("Career development", "Number of previous employers", "Retain", "Career mobility history"),
    "Over18": ("Technical", "Whether employee is over 18", "Exclude", "Expected constant: carries no information"),
    "OverTime": ("Work conditions", "Works overtime (Yes/No)", "Retain", "Workload indicator (business question Q4)"),
    "PercentSalaryHike": ("Performance", "Last salary increase in %", "Retain", "Compensation progression"),
    "PerformanceRating": ("Performance", "Performance rating, 1=Low .. 4=Outstanding", "Review", "Check variance: may only use part of the scale"),
    "RelationshipSatisfaction": ("Satisfaction", "Satisfaction with work relationships, 1=Low .. 4=Very High", "Retain", "Employee experience"),
    "StandardHours": ("Technical", "Standard working hours", "Exclude", "Expected constant: carries no information"),
    "StockOptionLevel": ("Compensation", "Stock option level 0..3", "Retain", "Non-salary compensation"),
    "TotalWorkingYears": ("Career development", "Total years of work experience", "Retain", "Experience; correlated with Age (proxy risk)"),
    "TrainingTimesLastYear": ("Career development", "Trainings attended last year", "Retain", "Development investment"),
    "WorkLifeBalance": ("Work conditions", "Work-life balance, 1=Bad .. 4=Best", "Retain", "Working conditions (Q5)"),
    "YearsAtCompany": ("Career development", "Tenure at company in years", "Retain", "Tenure"),
    "YearsInCurrentRole": ("Career development", "Years in current role", "Retain", "Career progression"),
    "YearsSinceLastPromotion": ("Career development", "Years since last promotion", "Retain", "Career progression"),
    "YearsWithCurrManager": ("Career development", "Years with current manager", "Retain", "Manager stability"),
}
