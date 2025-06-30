use anyhow::Result;
use lettre::{Message, SmtpTransport, Transport};

/// Send a plain text email using the local SMTP server.
pub fn send_email(from: &str, to: &str, subject: &str, body: &str) -> Result<()> {
    let email = Message::builder()
        .from(from.parse()?)
        .to(to.parse()?)
        .subject(subject)
        .body(body.to_string())?;

    let mailer = SmtpTransport::builder_dangerous("localhost").build();
    mailer.send(&email)?;
    Ok(())
}
