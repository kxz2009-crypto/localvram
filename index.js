export default {
async fetch(request) {
return new Response("Hello LocalVRAM! Your Worker is running.", {
headers: { "content-type": "text/plain" }
});
}
};
