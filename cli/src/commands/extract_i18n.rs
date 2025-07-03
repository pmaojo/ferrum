use anyhow::Result;
use std::path::PathBuf;

pub fn extract_i18n(dir: PathBuf, output: PathBuf) -> Result<()> {
    use regex::Regex;
    use std::collections::BTreeSet;
    use std::fs;
    use walkdir::WalkDir;

    let text_re = Regex::new(r">([^<]*[A-Za-z][^<]*)<")?;
    let placeholder_re = Regex::new(r#"placeholder=\"([^\"]+)\""#)?;
    let mut messages: BTreeSet<String> = BTreeSet::new();

    for entry in WalkDir::new(&dir).into_iter().filter_map(Result::ok) {
        let path = entry.path();
        if let Some(ext) = path.extension().and_then(|s| s.to_str()) {
            if ext == "tera" || ext == "yaml" {
                if let Ok(contents) = fs::read_to_string(path) {
                    for cap in text_re.captures_iter(&contents) {
                        messages.insert(cap[1].trim().to_string());
                    }
                    for cap in placeholder_re.captures_iter(&contents) {
                        messages.insert(cap[1].trim().to_string());
                    }
                }
            }
        }
    }

    let mut out = String::from("export const messages = {\n");
    for msg in &messages {
        let esc = msg.replace('"', "\\\"");
        out.push_str(&format!("  \"{}\": \"{}\",\n", esc, esc));
    }
    out.push_str("} as const;\n");

    if let Some(parent) = output.parent() {
        fs::create_dir_all(parent)?;
    }
    fs::write(&output, out)?;
    println!(
        "✅ Wrote {} messages to {}",
        messages.len(),
        output.display()
    );
    Ok(())
}

