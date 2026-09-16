import { createClient } from "jsr:@supabase/supabase-js@2";

const allowedCategories = new Set(["keamanan", "medis", "kebakaran", "kecelakaan", "bencana"]);
const allowedModes = new Set(["public", "silent"]);
const allowedScopes = new Set(["rt", "rw", "petugas"]);

Deno.serve(async (request) => {
  if (request.method !== "POST") return Response.json({ error: "method_not_allowed" }, { status: 405 });
  const auth = request.headers.get("Authorization") ?? "";
  const supabase = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_ANON_KEY")!, {
    global: { headers: { Authorization: auth } },
  });
  const { data: session, error: authError } = await supabase.auth.getUser();
  if (authError || !session.user) return Response.json({ error: "unauthorized" }, { status: 401 });

  const body = await request.json().catch(() => null);
  if (!body || !allowedCategories.has(body.category) || !allowedModes.has(body.mode) || !allowedScopes.has(body.scope)) {
    return Response.json({ error: "invalid_payload" }, { status: 400 });
  }
  const idempotencyKey = request.headers.get("Idempotency-Key");
  if (!idempotencyKey) return Response.json({ error: "idempotency_key_required" }, { status: 400 });

  const { data: profile } = await supabase.from("users").select("house_id,rt,houses(address,latitude,longitude)").eq("id", session.user.id).single();
  if (!profile) return Response.json({ error: "profile_not_found" }, { status: 404 });
  const { data: existing } = await supabase.from("emergency_alerts").select("id").eq("reporter_id", session.user.id).in("status", ["cancel_window", "active", "acknowledged", "responding"]).maybeSingle();
  if (existing) return Response.json({ error: "active_alert_exists" }, { status: 409 });

  const cancelDeadline = new Date(Date.now() + 10_000).toISOString();
  const house = Array.isArray(profile.houses) ? profile.houses[0] : profile.houses;
  const { data, error } = await supabase.from("emergency_alerts").insert({
    reporter_id: session.user.id,
    category: body.category,
    mode: body.mode,
    scope: body.scope,
    status: "cancel_window",
    latitude: body.latitude ?? house?.latitude ?? null,
    longitude: body.longitude ?? house?.longitude ?? null,
    address_snapshot: house?.address ?? `RT ${profile.rt}`,
    cancel_deadline: cancelDeadline,
    idempotency_key: idempotencyKey,
  }).select("id,status,cancel_deadline").single();
  if (error?.code === "23505") {
    const { data: duplicate } = await supabase.from("emergency_alerts").select("id,status,cancel_deadline").eq("reporter_id", session.user.id).eq("idempotency_key", idempotencyKey).single();
    return Response.json(duplicate, { status: 200 });
  }
  if (error) return Response.json({ error: "create_failed" }, { status: 500 });

  // Realtime membaca INSERT/UPDATE dari publication. Dispatcher terpisah mengubah
  // cancel_window menjadi active setelah deadline, lalu baru mengirim FCM/n8n.
  return Response.json(data, { status: 201 });
});
