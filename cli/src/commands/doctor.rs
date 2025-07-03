use anyhow::Result;
use std::path::PathBuf;

pub fn doctor() -> Result<()> {
    use std::fs;
    println!("🔎 Running ferrum doctor...");
    let env_path = PathBuf::from(".env");
    if !env_path.exists() {
        println!("⚠️  .env file not found");
        return Ok(());
    }
    let contents = fs::read_to_string(&env_path)?;
    let mut ok = true;
    for key in [
        "JWT_SECRET",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GITHUB_CLIENT_ID",
        "GITHUB_CLIENT_SECRET",
    ] {
        let value = contents
            .lines()
            .find(|l| l.starts_with(key))
            .and_then(|l| l.splitn(2, '=').nth(1))
            .map(|v| v.trim())
            .unwrap_or("");
        if value.is_empty() {
            println!("⚠️  {key} is missing or empty in .env");
            ok = false;
        }
    }
    if ok {
        println!("✅ .env looks good");
    }
    Ok(())
}

