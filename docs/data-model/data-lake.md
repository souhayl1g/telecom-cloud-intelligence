flowchart TB
  RAW["Raw\nSynthetic OSS KPIs\nSynthetic BSS Usage/Revenue"]
  PROC["Processed\nCleaned + aligned\nWindowed + features"]
  CUR["Curated\nJoined OSS+BSS\nAI outputs + correlation"]

  RAW --> PROC --> CUR

  AI["AI Service"]
  PROC --> AI
  AI --> CUR
