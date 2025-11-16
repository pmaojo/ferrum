use ferrum_compiler::{compile_policies, parse_dsl_yaml, ProjectPaths};
use std::fs;
use std::process::Command;
use tempfile::tempdir;

fn build_and_run(dir: &std::path::Path) -> String {
    let output = Command::new("cargo")
        .args(["run", "--quiet"])
        .current_dir(dir)
        .output()
        .expect("failed to run cargo");
    if !output.status.success() {
        eprintln!("stdout:\n{}", String::from_utf8_lossy(&output.stdout));
        eprintln!("stderr:\n{}", String::from_utf8_lossy(&output.stderr));
        panic!("cargo run failed");
    }
    String::from_utf8_lossy(&output.stdout).trim().to_string()
}

#[test]
fn role_based_policy_evaluates() {
    let yaml = "app:\n  name: demo\npolicies:\n  - name: isAdmin\n    guard: role:admin\n";
    let tmp = tempdir().unwrap();
    let file = tmp.path().join("dsl.yaml");
    fs::write(&file, yaml).unwrap();
    let dsl = parse_dsl_yaml(&file).unwrap();

    let out = tempdir().unwrap();
    let paths = ProjectPaths::new(out.path());
    compile_policies(&dsl, &paths).unwrap();

    let crate_dir = out.path().join("crate");
    fs::create_dir_all(crate_dir.join("src/policies")).unwrap();
    fs::copy(paths.backend.join("policies/mod.rs"), crate_dir.join("src/policies/mod.rs")).unwrap();
    fs::copy(paths.backend.join("policies/isadmin.rs"), crate_dir.join("src/policies/isadmin.rs")).unwrap();

    fs::write(
        crate_dir.join("Cargo.toml"),
        "[package]\nname=\"policy_test\"\nversion=\"0.1.0\"\nedition=\"2021\"\n\n[dependencies]\nserde = { version = \"1.0\", features = [\"derive\"] }\nserde_json = \"1.0\"\nbase64 = \"0.21\"\n",
    )
    .unwrap();

    let main_rs = format!(
        "mod policies;\nuse base64::engine::general_purpose::STANDARD;\nuse base64::Engine as _;\nfn main() {{\n    let payload = STANDARD.encode(r#\"{{\"roles\":[\"admin\"]}}\"#);\n    let token = format!(\"a.{{}}.b\", payload);\n    policies::set_request_context(&format!(\"jwt={{}}\", token));\n    println!(\"{{}}\", policies::evaluate_policy(\"isAdmin\"));\n}}\n"
    );
    fs::write(crate_dir.join("src/main.rs"), main_rs).unwrap();

    let output = build_and_run(&crate_dir);
    assert_eq!(output, "true");
}

#[test]
fn custom_guard_policy_evaluates() {
    let yaml = "app:\n  name: demo\npolicies:\n  - name: isAdmin\n    guard: check_admin\n";
    let tmp = tempdir().unwrap();
    let file = tmp.path().join("dsl.yaml");
    fs::write(&file, yaml).unwrap();
    let dsl = parse_dsl_yaml(&file).unwrap();

    let out = tempdir().unwrap();
    let paths = ProjectPaths::new(out.path());
    compile_policies(&dsl, &paths).unwrap();

    let crate_dir = out.path().join("crate");
    fs::create_dir_all(crate_dir.join("src/policies")).unwrap();
    let mut mod_rs = fs::read_to_string(paths.backend.join("policies/mod.rs")).unwrap();
    mod_rs.push_str("\npub fn check_admin() -> bool { true }\n");
    fs::write(crate_dir.join("src/policies/mod.rs"), mod_rs).unwrap();
    fs::copy(paths.backend.join("policies/isadmin.rs"), crate_dir.join("src/policies/isadmin.rs")).unwrap();

    fs::write(
        crate_dir.join("Cargo.toml"),
        "[package]\nname=\"policy_test\"\nversion=\"0.1.0\"\nedition=\"2021\"\n\n[dependencies]\nserde = { version = \"1.0\", features = [\"derive\"] }\nserde_json = \"1.0\"\nbase64 = \"0.21\"\n",
    )
    .unwrap();

    let main_rs = "mod policies;fn main(){println!(\"{}\", policies::evaluate_policy(\"isAdmin\"));}";
    fs::write(crate_dir.join("src/main.rs"), main_rs).unwrap();

    let output = build_and_run(&crate_dir);
    assert_eq!(output, "true");
}
