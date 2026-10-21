(function () {
    var meta = document.querySelector('meta[name="mta-version"]');
    var current = meta ? meta.content : "";
    var label = document.getElementById("app-version");
    if (label) {
        label.textContent = current && current !== "unknown" ? current : "";
    }

    async function check() {
        try {
            var response = await fetch("/version", { cache: "no-store" });
            if (!response.ok) {
                return;
            }
            var data = await response.json();
            if (!data.version || data.version === "unknown" || !current || current === "unknown") {
                return;
            }
            if (data.version !== current) {
                var url = new URL(window.location.href);
                url.searchParams.set("v", data.version);
                window.location.replace(url.toString());
            }
        } catch (err) {
            /* The board keeps showing the last good data until the app is back. */
        }
    }

    setInterval(check, 20000);
})();
