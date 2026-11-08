import "./shoelace-setup.js";

await customElements.whenDefined("sl-button");

(function () {
    var catalog = [];
    var selected = [];
    var reorderMode = false;
    var drag = null;
    var banner = document.getElementById("banner");
    var results = document.getElementById("results");
    var selectedList = document.getElementById("selected-list");
    var search = document.getElementById("search");
    var reorderButton = document.getElementById("reorder");
    var boardHint = document.getElementById("board-hint");
    var scrollPane = document.querySelector(".settings-scroll");

    function makeButton(options) {
        var button = document.createElement("sl-button");
        button.size = options.size || "large";
        button.variant = options.variant || "neutral";
        if (options.outline) {
            button.outline = true;
        }
        if (options.circle) {
            button.circle = true;
        }
        if (options.className) {
            button.className = options.className;
        }
        if (options.label) {
            button.setAttribute("aria-label", options.label);
        }
        if (options.pressed != null) {
            button.setAttribute("aria-pressed", options.pressed ? "true" : "false");
        }
        button.disabled = !!options.disabled;
        if (options.icon) {
            var icon = document.createElement("sl-icon");
            icon.name = options.icon;
            if (options.iconSlot) {
                icon.slot = options.iconSlot;
            }
            button.appendChild(icon);
        }
        if (options.text) {
            button.appendChild(document.createTextNode(options.text));
        }
        if (options.onClick) {
            button.addEventListener("click", options.onClick);
        }
        return button;
    }

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

    function updateReorderChrome() {
        reorderButton.textContent = reorderMode ? "Done" : "Reorder";
        reorderButton.variant = reorderMode ? "primary" : "neutral";
        reorderButton.setAttribute("aria-pressed", reorderMode ? "true" : "false");
        document.body.classList.toggle("is-reordering", reorderMode);
        selectedList.classList.toggle("is-reordering", reorderMode);
        boardHint.textContent = reorderMode
            ? "Drag a station by the handle to change the board order."
            : "These stations cycle in order. Tap a direction or a line to turn it off. Grey lines stay off the board.";
    }

    function setReorderMode(on) {
        if (on && selected.length < 2) {
            showBanner("Add at least two stations before reordering.", "");
            return;
        }
        endDrag();
        reorderMode = on;
        updateReorderChrome();
        renderSelected();
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
            var name = station ? station.name : entry.id;
            var card = document.createElement("article");
            card.className = "station-card" + (reorderMode ? " is-reorder-card" : "");
            card.dataset.index = String(index);

            var head = document.createElement("div");
            head.className = "card-head";

            if (reorderMode) {
                var handle = makeButton({
                    className: "drag-handle",
                    label: "Drag to reorder " + name,
                    icon: "grip-vertical"
                });
                bindHandle(handle, card);
                head.appendChild(handle);
            }

            var titleWrap = document.createElement("div");
            titleWrap.className = "card-title";
            var title = document.createElement("h3");
            title.textContent = name;
            titleWrap.appendChild(title);

            if (reorderMode) {
                var chips = document.createElement("div");
                chips.className = "result-lines card-lines";
                (station ? station.routes : []).forEach(function (route) {
                    if (entry.routes.indexOf(route.id) < 0) {
                        return;
                    }
                    var dot = document.createElement("span");
                    dot.className = "mini-bullet" + (route.express ? " express" : "");
                    dot.style.background = route.color;
                    dot.style.color = route.text_color;
                    dot.textContent = route.short;
                    chips.appendChild(dot);
                });
                titleWrap.appendChild(chips);
            }

            head.appendChild(titleWrap);

            if (!reorderMode) {
                var actions = document.createElement("div");
                actions.className = "card-actions";
                actions.appendChild(makeButton({
                    className: "icon-button",
                    label: "Remove " + name,
                    icon: "x-lg",
                    circle: true,
                    onClick: function () {
                        selected.splice(index, 1);
                        renderSelected();
                        renderResults();
                    }
                }));
                head.appendChild(actions);
            }

            card.dataset.stationId = entry.id;
            card.appendChild(head);

            if (!reorderMode) {
                var directions = document.createElement("div");
                directions.className = "choice-row";
                var directionOptions = station ? station.directions : [
                    { id: "N", label: "Northbound" },
                    { id: "S", label: "Southbound" }
                ];
                directionOptions.forEach(function (direction) {
                    var on = entry.directions.indexOf(direction.id) >= 0;
                    var button = makeButton({
                        className: "choice" + (on ? " is-on" : ""),
                        text: direction.label,
                        outline: !on,
                        pressed: on,
                        onClick: function () {
                            toggleList(entry.directions, direction.id);
                            if (!entry.directions.length) {
                                entry.directions.push(direction.id);
                            }
                            renderSelected();
                        }
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
            }

            selectedList.appendChild(card);
        });
    }

    function cardIndex(card) {
        return Array.prototype.indexOf.call(selectedList.querySelectorAll(".station-card"), card);
    }

    function bindHandle(handle, card) {
        handle.addEventListener("pointerdown", function (event) {
            if (!reorderMode || event.button) {
                return;
            }
            event.preventDefault();
            var index = cardIndex(card);
            if (index < 0) {
                return;
            }
            var rect = card.getBoundingClientRect();
            drag = {
                card: card,
                index: index,
                pointerId: event.pointerId,
                offsetY: event.clientY - rect.top,
                height: rect.height,
                lastY: event.clientY,
                autoScroll: 0,
                raf: 0
            };
            card.classList.add("is-dragging");
            card.style.width = rect.width + "px";
            card.style.height = rect.height + "px";
            card.style.top = rect.top + "px";
            card.style.left = rect.left + "px";
            insertPlaceholder(index, rect.height);
            // Keep the floating card out of list hit-testing / flex flow bookkeeping.
            document.body.appendChild(card);
            handle.setPointerCapture(event.pointerId);
            handle.addEventListener("pointermove", onDragMove);
            handle.addEventListener("pointerup", onDragEnd);
            handle.addEventListener("pointercancel", onDragEnd);
            moveDragCard(event.clientY);
            startAutoScroll();
        });
    }

    function insertPlaceholder(index, height) {
        var placeholder = document.createElement("div");
        placeholder.className = "station-placeholder";
        placeholder.style.height = height + "px";
        var cards = selectedList.querySelectorAll(".station-card");
        var reference = cards[index] || null;
        selectedList.insertBefore(placeholder, reference);
    }

    function placeholderNode() {
        return selectedList.querySelector(".station-placeholder");
    }

    function moveDragCard(clientY) {
        if (!drag) {
            return;
        }
        var top = clientY - drag.offsetY;
        drag.card.style.top = top + "px";
        var mid = top + drag.height / 2;
        var placeholder = placeholderNode();
        if (!placeholder) {
            return;
        }
        var siblings = Array.prototype.filter.call(selectedList.children, function (node) {
            return node.classList.contains("station-card") && node !== drag.card;
        });
        var insertBefore = null;
        for (var i = 0; i < siblings.length; i += 1) {
            var rect = siblings[i].getBoundingClientRect();
            if (mid < rect.top + rect.height / 2) {
                insertBefore = siblings[i];
                break;
            }
        }
        if (insertBefore) {
            selectedList.insertBefore(placeholder, insertBefore);
        } else {
            selectedList.appendChild(placeholder);
        }
    }

    function startAutoScroll() {
        if (!drag || drag.raf) {
            return;
        }
        function tick() {
            if (!drag) {
                return;
            }
            if (drag.autoScroll) {
                scrollPane.scrollTop += drag.autoScroll;
                moveDragCard(drag.lastY);
            }
            drag.raf = window.requestAnimationFrame(tick);
        }
        drag.raf = window.requestAnimationFrame(tick);
    }

    function onDragMove(event) {
        if (!drag || event.pointerId !== drag.pointerId) {
            return;
        }
        event.preventDefault();
        drag.lastY = event.clientY;
        moveDragCard(event.clientY);
        var paneRect = scrollPane.getBoundingClientRect();
        var edge = 56;
        if (event.clientY < paneRect.top + edge) {
            drag.autoScroll = -10;
        } else if (event.clientY > paneRect.bottom - edge) {
            drag.autoScroll = 10;
        } else {
            drag.autoScroll = 0;
        }
    }

    function onDragEnd(event) {
        if (!drag || event.pointerId !== drag.pointerId) {
            return;
        }
        var handle = event.currentTarget;
        handle.releasePointerCapture(event.pointerId);
        handle.removeEventListener("pointermove", onDragMove);
        handle.removeEventListener("pointerup", onDragEnd);
        handle.removeEventListener("pointercancel", onDragEnd);

        var placeholder = placeholderNode();
        var from = drag.index;
        var to = from;
        if (placeholder) {
            var nodes = Array.prototype.filter.call(selectedList.children, function (node) {
                return node === placeholder || (node.classList.contains("station-card") && node !== drag.card);
            });
            to = nodes.indexOf(placeholder);
            if (to < 0) {
                to = from;
            }
        }
        if (to !== from) {
            var item = selected.splice(from, 1)[0];
            selected.splice(to, 0, item);
        }
        endDrag();
        renderSelected();
    }

    function endDrag() {
        if (!drag) {
            return;
        }
        if (drag.raf) {
            window.cancelAnimationFrame(drag.raf);
        }
        if (drag.card) {
            drag.card.remove();
        }
        var placeholder = placeholderNode();
        if (placeholder) {
            placeholder.remove();
        }
        drag = null;
    }

    function toggleList(list, value) {
        var index = list.indexOf(value);
        if (index >= 0) {
            list.splice(index, 1);
        } else {
            list.push(value);
        }
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

            row.appendChild(makeButton({
                className: "add-button",
                text: already ? "Added" : "Add",
                variant: already ? "neutral" : "primary",
                disabled: already,
                onClick: function () { addStation(station); }
            }));
            results.appendChild(row);
        });
    }

    function payload() {
        return {
            trains_ahead: Number(document.getElementById("trains-ahead").value),
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
        if (reorderMode) {
            setReorderMode(false);
        }
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
            document.getElementById("trains-ahead").value = config.trains_ahead;
            document.getElementById("per-page").value = config.trains_per_page;
            document.getElementById("cycle").value = config.cycle_seconds;
            document.getElementById("zip").value = config.zip_code;
            updateReorderChrome();
            renderSelected();
            renderResults();
        } catch (err) {
            showBanner("Could not load stations. Is the app running?", "error");
        }
    }

    search.addEventListener("input", renderResults);
    reorderButton.addEventListener("click", function () {
        setReorderMode(!reorderMode);
    });
    document.getElementById("save").addEventListener("click", save);
    init();
})();
