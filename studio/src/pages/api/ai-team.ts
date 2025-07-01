export default async function handler(req: Request): Promise<Response> {
  const result = await fetch("http://localhost:8001/ai-team", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: await req.text(),
  });
  const json = await result.json();
  return new Response(JSON.stringify(json), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
