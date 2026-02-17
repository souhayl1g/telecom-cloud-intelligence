flowchart LR
    Engineer["Telecom Operations Engineer"]
    Analyst["Business Analyst"]

    UC1((View OSS KPIs))
    UC2((Detect Network Anomalies))
    UC3((View SLA Risk Score))
    UC4((View BSS Revenue/Usage))
    UC5((Detect Revenue Anomalies))
    UC6((Analyze OSS–BSS Correlation))
    UC7((Export Insights via API))

    Engineer --> UC1
    Engineer --> UC2
    Engineer --> UC3
    Engineer --> UC6
    Engineer --> UC7

    Analyst --> UC4
    Analyst --> UC5
    Analyst --> UC6
    Analyst --> UC7
