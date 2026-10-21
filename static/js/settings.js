(function () {
    var catalog = [];
    var selected = [];
    var banner = document.getElementById("banner");
    var results = document.getElementById("results");
    var selectedList = document.getElementById("selected-list");
    var search = document.getElementById("search");

    function showBanner(text, kind) {
        banner.hidden = !text;
        banner.textContent = text || "";
        banner.className = "banner" + (kind ? " banner-" + kind : "");
    }

    function stationById(id) {
        for (var i = 0; i < catalog.length; i += 1) {
            if (catalog[i].id === id) {
                return catalog[i];
            }
        }
        return null;
    }

    function bullet(route, pressed) {
        var button = document.createElement("button");
        button.type = "button";
        button.className = "route-bullet" + (route.express ? " express" : "") + (pressed ? "" : " is-dim");
        button.style.background = route.color;
        button.style.color = route.text_color;
        button.title = (route.name || route.short) + (pressed ? " (shown)" : " (hidden)");
        button.setAttribute("aria-pressed", pressed ? "true" : "false");
        button.setAttribute("aria-label", (route.name || route.short) + (pressed ? ", shown on the board" : ", hidden on the board"));
        var text = document.createElement("span");
        text.className = "bullet-text";
        text.textContent = route.short;
        button.appendChild(text);
        return button;
    }

    function renderSelected() {
        selectedList.innerHTML = "";
        if (!selected.length) {
            var empty = document.createElement("p");
            empty.className = "hint";
            empty.textContent = "No stations yet. Search below and add one.";
            selectedList.appendChild(empty);
            return;
        }
        selected.forEach(function (entry, index) {
            var station = stationById(entry.id);
            var card = document.createElement("article");
            card.className = "station-card";

            var head = document.createElement("div");
            head.className = "card-head";

            var title = document.createElement("h3");
            title.textContent = station ? station.name : entry.id;
            head.appendChild(title);

            var actions = document.createElement("div");
            actions.className = "card-actions";
            actions.appendChild(iconButton("Up", "↑", function () { move(index, -1); }, index === 0));
            actions.appendChild(iconButton("Down", "↓", function () { move(index, 1); }, index === selected.length - 1));
            actions.appendChild(iconButton("Remove " + (station ? station.name : entry.id), "✕", function () {
                selected.splice(index, 1);
                renderSelected();
                renderResults();
            }, false));
            head.appendChild(actions);
            card.appendChild(head);

            var directions = document.createElement("div");
            directions.className = "choice-row";
            var directionOptions = station ? station.directions : [
                { id: "N", label: "Northbound" },
                { id: "S", label: "Southbound" }
            ];
            directionOptions.forEach(function (direction) {
                var button = document.createElement("button");
                button.type = "button";
                button.className = "choice" + (entry.directions.indexOf(direction.id) >= 0 ? " is-on" : "");
                button.textContent = direction.label;
                button.addEventListener("click", function () {
                    toggleList(entry.directions, direction.id);
                    if (!entry.directions.length) {
                        entry.directions.push(direction.id);
                    }
                    renderSelected();
                });
                directions.appendChild(button);
            });
            card.appendChild(directions);

            var lines = document.createElement("div");
            lines.className = "choice-row line-row";
            (station ? station.routes : []).forEach(function (route) {
                var button = bullet(route, entry.routes.indexOf(route.id) >= 0);
                button.addEventListener("click", function () {
                    toggleList(entry.routes, route.id);
                    if (!entry.routes.length) {
                        entry.routes.push(route.id);
                    }
                    renderSelected();
                });
                lines.appendChild(button);
            });
            card.appendChild(lines);
            selectedList.appendChild(card);
        });
    }

    function iconButton(label, text, onClick, disabled) {
        var button = document.createElement("button");
        button.type = "button";
        button.className = "icon-button";
        button.textContent = text;
        button.setAttribute("aria-label", label);
        button.disabled = disabled;
        button.addEventListener("click", onClick);
        return button;
    }

    function toggleList(list, value) {
        var index = list.indexOf(value);
        if (index >= 0) {
            list.splice(index, 1);
        } else {
            list.push(value);
        }
    }

    function move(index, delta) {
        var next = index + delta;
        if (next < 0 || next >= selected.length) {
            return;
        }
        var item = selected.splice(index, 1)[0];
        selected.splice(next, 0, item);
        renderSelected();
    }

    function addStation(station) {
        if (selected.some(function (entry) { return entry.id === station.id; })) {
            return;
        }
        selected.push({
            id: station.id,
            directions: station.directions.map(function (direction) { return direction.id; }),
            routes: station.routes.map(function (route) { return route.id; })
        });
        renderSelected();
        renderResults();
    }

    function routeExact(station, query) {
        return station.routes.some(function (route) {
            return route.id.toLowerCase() === query || route.short.toLowerCase() === query;
        });
    }

    function matches(station, query) {
        if (!query) {
            return false;
        }
        if (station.name.toLowerCase().indexOf(query) >= 0) {
            return true;
        }
        return routeExact(station, query);
    }

    function renderResults() {
        var query = search.value.trim().toLowerCase();
        results.innerHTML = "";
        if (!query) {
            var hint = document.createElement("p");
            hint.className = "hint";
            hint.textContent = "Type a station name, or a line such as L, 6, or Q.";
            results.appendChild(hint);
            return;
        }
        var lineQuery = query.length <= 3 && !/^\d{2,}$/.test(query) && catalog.some(function (station) {
            return routeExact(station, query);
        });
        var found = catalog.filter(function (station) {
            return lineQuery ? routeExact(station, query) : matches(station, query);
        });
        found.sort(function (a, b) {
            var aStarts = a.name.toLowerCase().indexOf(query) === 0 ? 0 : 1;
            var bStarts = b.name.toLowerCase().indexOf(query) === 0 ? 0 : 1;
            if (aStarts !== bStarts) {
                return aStarts - bStarts;
            }
            return a.name.localeCompare(b.name) || a.id.localeCompare(b.id);
        });
        found = found.slice(0, 40);
        if (!found.length) {
            var none = document.createElement("p");
            none.className = "hint";
            none.textContent = "No stations match that search.";
            results.appendChild(none);
            return;
        }
        found.forEach(function (station) {
            var already = selected.some(function (entry) { return entry.id === station.id; });
            var row = document.createElement("div");
            row.className = "result-row";

            var info = document.createElement("div");
            info.className = "result-info";
            var name = document.createElement("div");
            name.className = "result-name";
            name.textContent = station.name;
            info.appendChild(name);
            var lines = document.createElement("div");
            lines.className = "result-lines";
            station.routes.forEach(function (route) {
                var dot = document.createElement("span");
                dot.className = "mini-bullet" + (route.express ? " express" : "");
                dot.style.background = route.color;
                dot.style.color = route.text_color;
                dot.textContent = route.short;
                lines.appendChild(dot);
            });
            info.appendChild(lines);
            row.appendChild(info);

            var button = document.createElement("button");
            button.type = "button";
            button.className = "add-button";
            button.textContent = already ? "Added" : "Add";
            button.disabled = already;
            button.addEventListener("click", function () { addStation(station); });
            row.appendChild(button);
            results.appendChild(row);
        });
    }

    function payload() {
        return {
            lookahead_minutes: Number(document.getElementById("lookahead").value),
            trains_per_page: Number(document.getElementById("per-page").value),
            cycle_seconds: Number(document.getElementById("cycle").value),
            zip_code: document.getElementById("zip").value.trim(),
            stations: selected.map(function (entry) {
                var station = stationById(entry.id);
                var allowed = station ? station.routes.map(function (route) { return route.id; }) : entry.routes;
                return {
                    id: entry.id,
                    directions: ["N", "S"].filter(function (direction) {
                        return entry.directions.indexOf(direction) >= 0;
                    }),
                    routes: allowed.filter(function (routeId) {
                        return entry.routes.indexOf(routeId) >= 0;
                    })
                };
            })
        };
    }

    async function save() {
        showBanner("Saving…", "");
        try {
            var response = await fetch("/api/config", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload())
            });
            var data = await response.json();
            if (!response.ok) {
                showBanner((data.errors || ["Could not save."]).join(" "), "error");
                return;
            }
            showBanner("Saved. The board picks this up within a few seconds.", "ok");
        } catch (err) {
            showBanner("Could not reach the app to save.", "error");
        }
    }

    async function init() {
        try {
            var responses = await Promise.all([
                fetch("/api/stations", { cache: "no-store" }),
                fetch("/api/config", { cache: "no-store" })
            ]);
            if (!responses[0].ok || !responses[1].ok) {
                throw new Error("settings unavailable");
            }
            var stationData = await responses[0].json();
            var config = await responses[1].json();
            catalog = stationData.stations || [];
            selected = (config.stations || []).map(function (station) {
                return {
                    id: station.id,
                    directions: station.directions.slice(),
                    routes: station.routes.slice()
                };
            });
            document.getElementById("lookahead").value = config.lookahead_minutes;
            document.getElementById("per-page").value = config.trains_per_page;
            document.getElementById("cycle").value = config.cycle_seconds;
            document.getElementById("zip").value = config.zip_code;
            renderSelected();
            renderResults();
        } catch (err) {
            showBanner("Could not load stations. Is the app running?", "error");
        }
    }

    search.addEventListener("input", renderResults);
    document.getElementById("save").addEventListener("click", save);
    init();
})();
