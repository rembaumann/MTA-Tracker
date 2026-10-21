(function () {
    var state = {
        groups: [],
        sections: [],
        routes: [],
        index: 0,
        selected: new Set(),
        paused: false,
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
    var controls = document.getElementById("controls");
    var picker = document.getElementById("line-picker");
    var pauseButton = document.getElementById("pause-cycle");
    var pageIndicator = document.getElementById("page-indicator");
    var stationName = document.getElementById("station-name");
    var direction = document.getElementById("direction");
    var cycleFill = document.getElementById("cycle-bar-fill");

    function storedLines() {
        try {
            var raw = JSON.parse(sessionStorage.getItem("mta-lines") || "[]");
            return new Set(Array.isArray(raw) ? raw : []);
        } catch (err) {
            return new Set();
        }
    }

    state.selected = storedLines();

    function persistLines() {
        sessionStorage.setItem("mta-lines", JSON.stringify(Array.from(state.selected)));
    }

    function sectionKey(section) {
        return section.station_id + ":" + section.page;
    }

    function rebuild() {
        var sections = [];
        state.groups.forEach(function (group) {
            var trains = group.trains || [];
            if (state.selected.size) {
                trains = trains.filter(function (train) {
                    return state.selected.has(train.route);
                });
            }
            if (!trains.length) {
                return;
            }
            var pages = Math.ceil(trains.length / state.perPage);
            for (var page = 0; page < pages; page += 1) {
                sections.push({
                    station: group.station,
                    station_id: group.station_id,
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

    function bulletLabel(route) {
        var sameShort = state.routes.filter(function (item) {
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
        text.textContent = className === "train-bullet" ? route.short : bulletLabel(route);
        bullet.appendChild(text);
        return bullet;
    }

    function formatMinutes(minutes) {
        if (minutes < 1) {
            return "NOW";
        }
        if (minutes < 2) {
            return "1 MIN";
        }
        return Math.round(minutes) + " MIN";
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

    function renderPicker() {
        picker.innerHTML = "";
        if (!state.routes.length) {
            return;
        }
        var all = document.createElement("button");
        all.type = "button";
        all.className = "line-all" + (state.selected.size ? "" : " is-active");
        all.textContent = "All";
        all.addEventListener("click", function () {
            state.selected.clear();
            persistLines();
            onFilterChange();
        });
        picker.appendChild(all);

        state.routes.forEach(function (route) {
            var button = document.createElement("button");
            button.type = "button";
            button.className = "route-bullet" + (route.express ? " express" : "");
            button.style.background = route.color;
            button.style.color = route.text_color;
            button.title = route.name || route.short;
            button.setAttribute("aria-label", route.name || route.short);
            button.setAttribute("aria-pressed", state.selected.has(route.id) ? "true" : "false");
            if (state.selected.size && !state.selected.has(route.id)) {
                button.classList.add("is-dim");
            }
            var text = document.createElement("span");
            text.className = "bullet-text";
            text.textContent = bulletLabel(route);
            button.appendChild(text);
            button.addEventListener("click", function () {
                toggleRoute(route.id);
            });
            picker.appendChild(button);
        });
    }

    function toggleRoute(routeId) {
        if (state.selected.size === 0) {
            state.selected = new Set([routeId]);
        } else if (state.selected.has(routeId)) {
            state.selected.delete(routeId);
        } else {
            state.selected.add(routeId);
        }
        if (state.selected.size === state.routes.length) {
            state.selected.clear();
        }
        persistLines();
        onFilterChange();
    }

    function onFilterChange() {
        state.index = 0;
        rebuild();
        renderPicker();
        render();
        kickCycle(true);
    }

    function render() {
        var hasSections = state.sections.length > 0;
        loading.hidden = true;
        errorBox.hidden = true;
        empty.hidden = hasSections;
        trainsList.hidden = !hasSections;
        controls.classList.toggle("is-disabled", !hasSections);

        if (!hasSections) {
            stationName.textContent = "No trains";
            direction.hidden = true;
            pageIndicator.textContent = "–";
            stopCycleBar();
            var filtered = state.selected.size > 0;
            document.getElementById("empty-title").textContent = filtered
                ? "No trains on those lines"
                : "No upcoming trains";
            document.getElementById("empty-body").textContent = filtered
                ? "Try All, or another line."
                : "Nothing is due in the current window.";
            return;
        }

        var section = state.sections[state.index];
        stationName.textContent = section.station;
        direction.hidden = false;
        direction.textContent = section.direction;
        direction.className = "direction direction-" + section.direction_id.toLowerCase();

        trainsList.innerHTML = "";
        section.trains.forEach(function (train) {
            var route = routeById(train.route);
            var dest = splitDestination(train.destination);
            var item = document.createElement("li");
            item.className = "train-item";

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

            var time = document.createElement("div");
            time.className = "train-time";
            time.textContent = formatMinutes(train.minutes);

            item.appendChild(identity);
            item.appendChild(time);
            trainsList.appendChild(item);
        });

        pageIndicator.textContent = state.paused
            ? "Paused " + (state.index + 1) + "/" + state.sections.length
            : (state.index + 1) + " / " + state.sections.length;
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
        if (state.paused || state.sections.length < 2) {
            return;
        }
        window.requestAnimationFrame(function () {
            cycleFill.style.transition = "transform " + state.cycleSeconds + "s linear";
            cycleFill.style.transform = "scaleX(1)";
        });
    }

    function startTimer() {
        stopTimer();
        if (state.paused || state.sections.length < 2) {
            stopCycleBar();
            return;
        }
        restartCycleBar();
        state.timer = setInterval(function () {
            state.index = (state.index + 1) % state.sections.length;
            render();
            restartCycleBar();
        }, state.cycleSeconds * 1000);
    }

    function kickCycle(resetBar) {
        clearTimeout(state.resumeTimer);
        state.resumeTimer = null;
        if (state.paused) {
            stopTimer();
            stopCycleBar();
            return;
        }
        if (resetBar) {
            startTimer();
        }
    }

    function step(delta) {
        if (!state.sections.length) {
            return;
        }
        state.index = (state.index + delta + state.sections.length) % state.sections.length;
        render();
        if (state.paused) {
            return;
        }
        stopTimer();
        stopCycleBar();
        clearTimeout(state.resumeTimer);
        state.resumeTimer = setTimeout(function () {
            if (!state.paused) {
                startTimer();
            }
        }, 20000);
    }

    function setPaused(paused) {
        state.paused = paused;
        pauseButton.textContent = paused ? "Resume" : "Pause";
        pauseButton.setAttribute("aria-pressed", paused ? "true" : "false");
        clearTimeout(state.resumeTimer);
        render();
        if (paused) {
            stopTimer();
            stopCycleBar();
        } else {
            startTimer();
        }
    }

    function showError(message) {
        loading.hidden = true;
        empty.hidden = true;
        trainsList.hidden = true;
        errorBox.hidden = false;
        document.getElementById("error-body").textContent = message;
        stationName.textContent = "MTA Tracker";
        direction.hidden = true;
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
            state.perPage = data.trains_per_page || 5;
            state.cycleSeconds = data.cycle_seconds || 10;
            state.ready = true;

            var available = new Set(state.routes.map(function (route) { return route.id; }));
            state.selected.forEach(function (routeId) {
                if (!available.has(routeId)) {
                    state.selected.delete(routeId);
                }
            });

            rebuild();
            if (previousKey) {
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
            renderPicker();
            render();
            if (state.sections.length < 2 || state.paused) {
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

    document.getElementById("prev-page").addEventListener("click", function () { step(-1); });
    document.getElementById("next-page").addEventListener("click", function () { step(1); });
    pauseButton.addEventListener("click", function () { setPaused(!state.paused); });
    document.getElementById("retry").addEventListener("click", function () {
        errorBox.hidden = true;
        loading.hidden = false;
        fetchData();
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "ArrowRight") {
            step(1);
        } else if (event.key === "ArrowLeft") {
            step(-1);
        } else if (event.key === " ") {
            event.preventDefault();
            setPaused(!state.paused);
        }
    });

    document.addEventListener("visibilitychange", function () {
        if (document.hidden) {
            stopTimer();
            stopCycleBar();
        } else if (!state.paused) {
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
