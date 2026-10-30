(function () {
    var HOLD_MS = 20000;
    var state = {
        groups: [],
        sections: [],
        routes: [],
        stations: [],
        stationKey: "",
        index: 0,
        pinned: null,
        holding: false,
        perPage: 5,
        cycleSeconds: 10,
        timer: null,
        resumeTimer: null,
        ready: false,
        hasShown: false
    };

    var trainsList = document.getElementById("trains-list");
    var loading = document.getElementById("loading");
    var empty = document.getElementById("empty");
    var errorBox = document.getElementById("error");
    var prevButton = document.getElementById("prev-page");
    var nextButton = document.getElementById("next-page");
    var pageIndicator = document.getElementById("page-indicator");
    var stationButton = document.getElementById("station-button");
    var stationName = document.getElementById("station-name");
    var stationMenu = document.getElementById("station-menu");
    var direction = document.getElementById("direction");
    var cycleFill = document.getElementById("cycle-bar-fill");

    function sectionKey(section) {
        return section.station_id + ":" + section.page;
    }

    function parentId(group) {
        return group.parent_id || String(group.station_id || "").slice(0, -1);
    }

    function rebuild() {
        var sections = [];
        state.groups.forEach(function (group) {
            var trains = group.trains || [];
            if (!trains.length) {
                return;
            }
            var pages = Math.ceil(trains.length / state.perPage);
            for (var page = 0; page < pages; page += 1) {
                sections.push({
                    station: group.station,
                    station_id: group.station_id,
                    parent_id: parentId(group),
                    direction: group.direction,
                    direction_id: group.direction_id,
                    page: page + 1,
                    total_pages: pages,
                    trains: trains.slice(page * state.perPage, (page + 1) * state.perPage)
                });
            }
        });
        state.sections = sections;
        if (state.index >= sections.length) {
            state.index = 0;
        }
    }

    function routeById(routeId) {
        for (var i = 0; i < state.routes.length; i += 1) {
            if (state.routes[i].id === routeId) {
                return state.routes[i];
            }
        }
        return {
            id: routeId,
            short: routeId,
            name: routeId,
            color: "#808183",
            text_color: "#FFFFFF",
            express: routeId.slice(-1) === "X"
        };
    }

    function bulletLabel(route, routes) {
        var sameShort = routes.filter(function (item) {
            return item.short === route.short;
        });
        return sameShort.length > 1 ? route.id : route.short;
    }

    function makeBullet(route, className) {
        var bullet = document.createElement("span");
        bullet.className = className + (route.express ? " express" : "");
        bullet.style.background = route.color;
        bullet.style.color = route.text_color;
        bullet.title = route.name || route.short;
        var text = document.createElement("span");
        text.className = "bullet-text";
        if (className === "train-bullet") {
            text.textContent = route.express ? route.short.replace(/X$/, "") : route.short;
        } else {
            text.textContent = bulletLabel(route, state.routes);
        }
        bullet.appendChild(text);
        return bullet;
    }

    function makeTime(minutes) {
        var time = document.createElement("div");
        time.className = "train-time";
        var value = document.createElement("span");
        value.className = "train-time-value";
        time.appendChild(value);
        if (minutes < 1) {
            value.textContent = "NOW";
            return time;
        }
        value.textContent = minutes < 2 ? "1" : String(Math.round(minutes));
        var unit = document.createElement("span");
        unit.className = "train-time-unit";
        unit.textContent = "MIN";
        time.appendChild(unit);
        return time;
    }

    function splitDestination(destination) {
        if (!destination) {
            return { primary: "", secondary: "" };
        }
        var parts = destination.split("-");
        if (parts.length < 2) {
            return { primary: destination, secondary: "" };
        }
        return {
            primary: parts[0].trim(),
            secondary: parts.slice(1).join("-").trim()
        };
    }

    function currentParentId() {
        if (state.pinned) {
            return state.pinned.id;
        }
        var section = state.sections[state.index];
        return section ? section.parent_id : null;
    }

    function stationSignature(stations) {
        return stations.map(function (station) {
            var routes = (station.routes || []).map(function (route) { return route.id; }).join(",");
            return station.id + ":" + routes;
        }).join("|");
    }

    function renderMenu() {
        stationMenu.innerHTML = "";
        state.stations.forEach(function (station) {
            var option = document.createElement("button");
            option.type = "button";
            option.className = "station-option";
            option.setAttribute("role", "option");
            option.dataset.stationId = station.id;

            var name = document.createElement("span");
            name.className = "station-option-name";
            name.textContent = station.name;
            option.appendChild(name);

            var lines = document.createElement("span");
            lines.className = "menu-lines";
            (station.routes || []).forEach(function (route) {
                var bullet = document.createElement("span");
                bullet.className = "menu-bullet";
                bullet.style.background = route.color;
                bullet.style.color = route.text_color;
                bullet.textContent = bulletLabel(route, station.routes || []);
                lines.appendChild(bullet);
            });
            option.appendChild(lines);
            option.addEventListener("click", function () {
                jumpToStation(station.id);
            });
            stationMenu.appendChild(option);
        });
        markCurrentStation();
    }

    function markCurrentStation() {
        var current = currentParentId();
        var options = stationMenu.querySelectorAll(".station-option");
        options.forEach(function (option) {
            var selected = option.dataset.stationId === current;
            option.classList.toggle("is-current", selected);
            option.setAttribute("aria-selected", selected ? "true" : "false");
        });
    }

    function menuOpen() {
        return !stationMenu.hidden;
    }

    function closeMenu() {
        stationMenu.hidden = true;
        stationButton.setAttribute("aria-expanded", "false");
    }

    function toggleMenu() {
        if (!state.stations.length) {
            return;
        }
        if (menuOpen()) {
            closeMenu();
            return;
        }
        renderMenu();
        stationMenu.hidden = false;
        stationButton.setAttribute("aria-expanded", "true");
    }

    function setEmptyCopy(title, body) {
        document.getElementById("empty-title").textContent = title;
        document.getElementById("empty-body").textContent = body;
    }

    function setArrows() {
        var enabled = state.sections.length > 1;
        prevButton.disabled = !enabled;
        nextButton.disabled = !enabled;
    }

    function renderPinned() {
        loading.hidden = true;
        errorBox.hidden = true;
        trainsList.hidden = true;
        empty.hidden = false;
        stationName.textContent = state.pinned.name;
        direction.hidden = true;
        setEmptyCopy("No upcoming trains", "Nothing is due at this station in the current window.");
        pageIndicator.textContent = state.holding ? "Holding" : "";
        setArrows();
        markCurrentStation();
    }

    function render() {
        if (state.pinned) {
            var match = -1;
            for (var i = 0; i < state.sections.length; i += 1) {
                if (state.sections[i].parent_id === state.pinned.id) {
                    match = i;
                    break;
                }
            }
            if (match >= 0) {
                state.index = match;
                state.pinned = null;
            } else {
                renderPinned();
                return;
            }
        }

        var hasSections = state.sections.length > 0;
        loading.hidden = true;
        errorBox.hidden = true;
        empty.hidden = hasSections;
        trainsList.hidden = !hasSections;
        setArrows();

        if (!hasSections) {
            stationName.textContent = "No trains";
            direction.hidden = true;
            pageIndicator.textContent = "";
            stopCycleBar();
            setEmptyCopy("No upcoming trains", "Nothing is due in the current window.");
            markCurrentStation();
            return;
        }

        var section = state.sections[state.index];
        stationName.textContent = section.station;
        direction.hidden = false;
        direction.textContent = section.direction;
        direction.className = "direction direction-" + String(section.direction_id).toLowerCase();

        trainsList.innerHTML = "";
        trainsList.style.setProperty("--rows", state.perPage);
        section.trains.forEach(function (train, index) {
            var route = routeById(train.route);
            var dest = splitDestination(train.destination);
            var item = document.createElement("li");
            item.className = "train-item";

            var position = document.createElement("div");
            position.className = "train-position";
            position.textContent = (section.page - 1) * state.perPage + index + 1;

            var panel = document.createElement("div");
            panel.className = "train-panel";

            var identity = document.createElement("div");
            identity.className = "train-identity";
            identity.appendChild(makeBullet(route, "train-bullet"));

            var names = document.createElement("div");
            names.className = "train-names";
            if (dest.primary) {
                var primary = document.createElement("div");
                primary.className = "train-destination";
                primary.textContent = dest.primary;
                names.appendChild(primary);
            }
            if (dest.secondary) {
                var secondary = document.createElement("div");
                secondary.className = "train-destination-secondary";
                secondary.textContent = dest.secondary;
                names.appendChild(secondary);
            }
            identity.appendChild(names);

            panel.appendChild(identity);
            panel.appendChild(makeTime(train.minutes));
            item.appendChild(position);
            item.appendChild(panel);
            trainsList.appendChild(item);
        });

        var label = (state.index + 1) + " / " + state.sections.length;
        pageIndicator.textContent = state.holding ? label + " · holding" : label;
        markCurrentStation();
    }

    function stopTimer() {
        if (state.timer) {
            clearInterval(state.timer);
            state.timer = null;
        }
    }

    function stopCycleBar() {
        cycleFill.style.transition = "none";
        cycleFill.style.transform = "scaleX(0)";
    }

    function restartCycleBar() {
        stopCycleBar();
        if (state.holding || state.sections.length < 2) {
            return;
        }
        window.requestAnimationFrame(function () {
            cycleFill.style.transition = "transform " + state.cycleSeconds + "s linear";
            cycleFill.style.transform = "scaleX(1)";
        });
    }

    function startTimer() {
        stopTimer();
        state.holding = false;
        if (state.sections.length < 2) {
            stopCycleBar();
            render();
            return;
        }
        restartCycleBar();
        state.timer = setInterval(function () {
            state.index = (state.index + 1) % state.sections.length;
            render();
            restartCycleBar();
        }, state.cycleSeconds * 1000);
        render();
    }

    function holdCycle() {
        state.holding = true;
        stopTimer();
        stopCycleBar();
        clearTimeout(state.resumeTimer);
        state.resumeTimer = setTimeout(function () {
            state.resumeTimer = null;
            state.pinned = null;
            startTimer();
        }, HOLD_MS);
        render();
    }

    function step(delta) {
        closeMenu();
        if (state.sections.length < 2) {
            return;
        }
        state.pinned = null;
        state.index = (state.index + delta + state.sections.length) % state.sections.length;
        holdCycle();
    }

    function jumpToStation(stationId) {
        closeMenu();
        var station = null;
        for (var i = 0; i < state.stations.length; i += 1) {
            if (state.stations[i].id === stationId) {
                station = state.stations[i];
                break;
            }
        }
        var index = -1;
        for (var j = 0; j < state.sections.length; j += 1) {
            if (state.sections[j].parent_id === stationId) {
                index = j;
                break;
            }
        }
        if (index >= 0) {
            state.pinned = null;
            state.index = index;
        } else if (station) {
            state.pinned = station;
        }
        holdCycle();
    }

    function showError(message) {
        loading.hidden = true;
        empty.hidden = true;
        trainsList.hidden = true;
        errorBox.hidden = false;
        document.getElementById("error-body").textContent = message;
        stationName.textContent = "MTA Tracker";
        direction.hidden = true;
        setArrows();
    }

    function applyTemperature(value) {
        var wrap = document.getElementById("temperature-wrap");
        if (value === null || value === undefined) {
            wrap.hidden = true;
            return;
        }
        wrap.hidden = false;
        document.getElementById("temperature").textContent = value;
    }

    async function fetchData() {
        try {
            var response = await fetch("/api/data", { cache: "no-store" });
            if (!response.ok) {
                throw new Error("Board data was not available.");
            }
            var data = await response.json();
            if (!data.ready) {
                return;
            }
            var previousKey = state.sections[state.index] ? sectionKey(state.sections[state.index]) : null;
            var previousCycle = state.cycleSeconds;
            state.groups = data.groups || [];
            state.routes = data.routes || [];
            state.stations = data.stations || [];
            state.perPage = data.trains_per_page || 5;
            state.cycleSeconds = data.cycle_seconds || 10;
            state.ready = true;

            var signature = stationSignature(state.stations);
            var stationsChanged = signature !== state.stationKey;
            state.stationKey = signature;

            rebuild();
            if (state.pinned) {
                var pinnedIndex = -1;
                for (var i = 0; i < state.sections.length; i += 1) {
                    if (state.sections[i].parent_id === state.pinned.id) {
                        pinnedIndex = i;
                        break;
                    }
                }
                if (pinnedIndex >= 0) {
                    state.index = pinnedIndex;
                    state.pinned = null;
                }
            } else if (previousKey) {
                var kept = state.sections.findIndex(function (section) {
                    return sectionKey(section) === previousKey;
                });
                if (kept >= 0) {
                    state.index = kept;
                }
            }

            document.getElementById("last-updated").textContent = data.last_updated || "--";
            document.getElementById("status-note").textContent = data.error && state.groups.length ? "Feed interrupted" : "";
            applyTemperature(data.temperature);

            if (data.error && !state.groups.length && !state.hasShown) {
                showError(data.error);
                return;
            }

            state.hasShown = true;
            if (stationsChanged || menuOpen()) {
                renderMenu();
            }
            render();
            if (state.sections.length < 2 || state.holding) {
                stopTimer();
                stopCycleBar();
            } else if (!state.timer || previousCycle !== state.cycleSeconds) {
                startTimer();
            }
        } catch (err) {
            if (!state.hasShown) {
                showError("Check the connection and try again.");
            } else {
                document.getElementById("status-note").textContent = "Update failed";
            }
        }
    }

    prevButton.addEventListener("click", function () { step(-1); });
    nextButton.addEventListener("click", function () { step(1); });
    stationButton.addEventListener("click", function (event) {
        event.stopPropagation();
        toggleMenu();
    });
    document.getElementById("retry").addEventListener("click", function () {
        errorBox.hidden = true;
        loading.hidden = false;
        fetchData();
    });

    document.addEventListener("click", function (event) {
        if (!menuOpen()) {
            return;
        }
        if (stationMenu.contains(event.target) || stationButton.contains(event.target)) {
            return;
        }
        closeMenu();
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeMenu();
        } else if (event.key === "ArrowRight") {
            step(1);
        } else if (event.key === "ArrowLeft") {
            step(-1);
        }
    });

    document.addEventListener("visibilitychange", function () {
        if (document.hidden) {
            stopTimer();
            stopCycleBar();
        } else if (!state.holding && state.sections.length > 1) {
            startTimer();
        }
    });

    fetchData();
    setInterval(fetchData, 30000);
    fetch("/api/temperature", { cache: "no-store" })
        .then(function (response) { return response.json(); })
        .then(function (data) { applyTemperature(data.temperature); })
        .catch(function () {});
})();
