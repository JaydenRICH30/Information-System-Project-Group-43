import os

layout_addon = "\""

    /* --- Layout & Alignment Enhancements --- */
    .product-card {
      display: flex !important;
      flex-direction: column;
      height: 100%;
    }
    .product-card img {
      border-top-left-radius: 23px;
      border-top-right-radius: 23px;
      object-fit: cover;
    }
    .product-copy, .product-card .content {
      display: flex;
      flex-direction: column;
      flex-grow: 1;
    }
    /* Push the price/action level to the bottom of the card */
    .product-copy .level:last-child, .product-card .content .level:last-child, .product-card .content .mt-auto {
      margin-top: auto;
      margin-bottom: 0 !important;
    }
    .panel-box, .box {
      padding: 32px;
    }
    @media (max-width: 768px) {
      .panel-box, .box { padding: 20px; }
      .metrics { gap: 16px !important; }
    }
    .metrics {
      gap: 24px;
    }
    .metric-card {
      display: flex;
      flex-direction: column;
      justify-content: center;
      padding: 24px;
    }
    .field:not(:last-child) {
      margin-bottom: 1.5rem;
    }
    label.label {
      font-weight: 600;
      color: rgba(0, 0, 0, 0.75);
      margin-bottom: 0.75rem;
    }
    .level {
      align-items: center;
    }
"\""

template_dir = r"c:\code\202602\0414\new300\DjangoProject\templates"
exclude = ["Login.html", "Register.html"]

for root, _, files in os.walk(template_dir):
    for file in files:
        if file.endswith(".html") and file not in exclude:
            path = os.path.join(root, file)
            if "includes" in path.replace("\\\\", "/"): continue
            
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                
            if "/* --- Layout & Alignment Enhancements --- */" in content:
                print(f"Skipping {file}")
                continue
                
            new_content = content.replace("</style>", layout_addon + "</style>")
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"Patched {file}")
