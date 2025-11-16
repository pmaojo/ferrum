use anyhow::Result;
use std::path::PathBuf;

pub fn plugin_docs(plugin: String) -> Result<()> {
    use std::fs;

    let name = plugin
        .split('/')
        .last()
        .unwrap_or(&plugin)
        .trim_end_matches(".git");

    // First try built-in docs
    let builtin = PathBuf::from(format!("docs/plugins/{name}.md"));
    if builtin.exists() {
        let contents = fs::read_to_string(builtin)?;
        println!("{}", contents);
        return Ok(());
    }

    // Then check installed plugin directories
    let plugins_file = PathBuf::from(".ferrum/plugins.txt");
    if plugins_file.exists() {
        let list = fs::read_to_string(&plugins_file)?;
        for line in list.lines() {
            let path = PathBuf::from(line.trim());
            let dir_name = path
                .file_name()
                .map(|s| s.to_string_lossy())
                .unwrap_or_default();
            if dir_name == name || line.trim() == plugin {
                let readme = path.join("README.md");
                if readme.exists() {
                    let contents = fs::read_to_string(readme)?;
                    println!("{}", contents);
                    return Ok(());
                }
            }
        }
    }

    // Finally, allow passing a direct path
    let direct = PathBuf::from(&plugin).join("README.md");
    if direct.exists() {
        let contents = fs::read_to_string(direct)?;
        println!("{}", contents);
        return Ok(());
    }

    println!("No docs found for {plugin}");
    Ok(())
}

