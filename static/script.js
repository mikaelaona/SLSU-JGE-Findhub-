/* =========================================
   SLSU-JGE FINDHUB
   Main JavaScript
   ========================================= */

"use strict";

document.addEventListener("DOMContentLoaded", function () {
    /* ---------- DARK MODE ---------- */

    const themeToggle = document.getElementById("themeToggle");
    const themeIcon = document.getElementById("themeIcon");
    const themeLabel = document.querySelector(".theme-label");

    function applyTheme(theme) {
        const selectedTheme = theme === "dark" ? "dark" : "light";

        document.documentElement.setAttribute("data-theme", selectedTheme);

        if (themeIcon) {
            themeIcon.textContent = selectedTheme === "dark" ? "☀" : "☾";
        }

        if (themeLabel) {
            themeLabel.textContent =
                selectedTheme === "dark" ? "Light mode" : "Dark mode";
        }

        if (themeToggle) {
            const nextTheme =
                selectedTheme === "dark" ? "light" : "dark";

            themeToggle.setAttribute(
                "aria-label",
                "Switch to " + nextTheme + " mode"
            );

            themeToggle.setAttribute(
                "title",
                "Switch to " + nextTheme + " mode"
            );

            themeToggle.setAttribute("aria-pressed", String(selectedTheme === "dark"));
        }
    }

    let savedTheme = "light";

    try {
        const storedTheme = localStorage.getItem("slsu-findhub-theme");

        if (storedTheme === "dark" || storedTheme === "light") {
            savedTheme = storedTheme;
        } else if (
            window.matchMedia &&
            window.matchMedia("(prefers-color-scheme: dark)").matches
        ) {
            savedTheme = "dark";
        }
    } catch (error) {
        // The website still works if browser storage is unavailable.
    }

    applyTheme(savedTheme);

    if (themeToggle) {
        themeToggle.addEventListener("click", function () {
            const currentTheme =
                document.documentElement.getAttribute("data-theme") || "light";

            const newTheme = currentTheme === "dark" ? "light" : "dark";

            applyTheme(newTheme);

            try {
                localStorage.setItem("slsu-findhub-theme", newTheme);
            } catch (error) {
                // Theme remains active until the page is refreshed.
            }
        });
    }

    /* ---------- MOBILE NAVIGATION ---------- */

    const menuToggle = document.getElementById("menuToggle");
    const navLinks = document.querySelector(".nav-links");

    if (menuToggle && navLinks) {
        menuToggle.setAttribute("aria-expanded", "false");

        menuToggle.addEventListener("click", function () {
            const isOpen =
                navLinks.classList.contains("is-open") ||
                navLinks.classList.contains("open") ||
                navLinks.classList.contains("active");

            navLinks.classList.remove("open", "active");
            navLinks.classList.toggle("is-open", !isOpen);

            menuToggle.setAttribute("aria-expanded", String(!isOpen));
            menuToggle.setAttribute(
                "aria-label",
                isOpen ? "Open navigation menu" : "Close navigation menu"
            );

            menuToggle.textContent = isOpen ? "☰" : "✕";
        });

        navLinks.querySelectorAll("a").forEach(function (link) {
            link.addEventListener("click", function () {
                if (window.innerWidth <= 760) {
                    navLinks.classList.remove("is-open", "open", "active");
                    menuToggle.setAttribute("aria-expanded", "false");
                    menuToggle.setAttribute("aria-label", "Open navigation menu");
                    menuToggle.textContent = "☰";
                }
            });
        });

        window.addEventListener("resize", function () {
            if (window.innerWidth > 760) {
                navLinks.classList.remove("is-open", "open", "active");
                menuToggle.setAttribute("aria-expanded", "false");
                menuToggle.textContent = "☰";
            }
        });
    }

    /* ---------- PASSWORD SHOW / HIDE ---------- */

    document.querySelectorAll("[data-password-toggle]").forEach(function (button) {
        button.addEventListener("click", function () {
            const targetId = button.getAttribute("data-password-toggle");
            const passwordInput = document.getElementById(targetId);

            if (!passwordInput) {
                return;
            }

            const isPassword = passwordInput.type === "password";

            passwordInput.type = isPassword ? "text" : "password";
            button.textContent = isPassword ? "Hide" : "Show";
            button.setAttribute(
                "aria-label",
                isPassword ? "Hide password" : "Show password"
            );
        });
    });

    /* Support the password toggle used by admin_login.html. */
    document.querySelectorAll(".password-toggle").forEach(function (button) {
        button.addEventListener("click", function () {
            const wrapper = button.closest(".password-wrapper");
            const passwordInput = wrapper
                ? wrapper.querySelector('input[type="password"], input[type="text"]')
                : null;

            if (!passwordInput) {
                return;
            }

            const isPassword = passwordInput.type === "password";

            passwordInput.type = isPassword ? "text" : "password";
            button.textContent = isPassword ? "Hide" : "Show";
        });
    });

    /* ---------- ITEM SEARCH AND FILTER ---------- */

    const itemSearch = document.getElementById("itemSearch");
    const statusFilter = document.getElementById("statusFilter");
    const itemCards = Array.from(document.querySelectorAll(".item-card"));
    const noResults = document.getElementById("noResults");

    function filterItems() {
        if (itemCards.length === 0) {
            return;
        }

        const query = itemSearch ? itemSearch.value.trim().toLowerCase() : "";
        const selectedStatus = statusFilter
            ? statusFilter.value.trim().toLowerCase()
            : "all";

        let visibleCount = 0;

        itemCards.forEach(function (card) {
            const searchableText = card.textContent.toLowerCase();

            const cardStatusElement = card.querySelector(
                ".status-badge, .badge, .status-pill"
            );

            const cardStatus = cardStatusElement
                ? cardStatusElement.textContent.trim().toLowerCase()
                : "";

            const matchesQuery = searchableText.includes(query);

            const matchesStatus =
                selectedStatus === "" ||
                selectedStatus === "all" ||
                cardStatus.includes(selectedStatus);

            const isVisible = matchesQuery && matchesStatus;

            card.hidden = !isVisible;

            if (isVisible) {
                visibleCount++;
            }
        });

        if (noResults) {
            noResults.hidden = visibleCount > 0;
        }
    }

    if (itemSearch) {
        itemSearch.addEventListener("input", filterItems);
    }

    if (statusFilter) {
        statusFilter.addEventListener("change", filterItems);
    }

    /* ---------- ADMIN TABLE SEARCH ---------- */

    const adminSearch = document.getElementById("adminSearch");
    const adminStatusFilter = document.getElementById("adminStatusFilter");
    const adminRows = Array.from(
        document.querySelectorAll("[data-admin-item], .admin-item-row")
    );
    const adminNoResults = document.getElementById("adminNoResults");

    function filterAdminRows() {
        if (adminRows.length === 0) {
            return;
        }

        const query = adminSearch
            ? adminSearch.value.trim().toLowerCase()
            : "";

        const selectedStatus = adminStatusFilter
            ? adminStatusFilter.value.trim().toLowerCase()
            : "all";

        let visibleCount = 0;

        adminRows.forEach(function (row) {
            const rowText = row.textContent.toLowerCase();
            const statusSelect = row.querySelector("select");

            const rowStatus = statusSelect
                ? statusSelect.value.toLowerCase()
                : row.getAttribute("data-status") || "";

            const matchesQuery = rowText.includes(query);

            const matchesStatus =
                selectedStatus === "" ||
                selectedStatus === "all" ||
                rowStatus === selectedStatus;

            const isVisible = matchesQuery && matchesStatus;

            row.hidden = !isVisible;

            if (isVisible) {
                visibleCount++;
            }
        });

        if (adminNoResults) {
            adminNoResults.hidden = visibleCount > 0;
        }
    }

    if (adminSearch) {
        adminSearch.addEventListener("input", filterAdminRows);
    }

    if (adminStatusFilter) {
        adminStatusFilter.addEventListener("change", filterAdminRows);
    }

    /* ---------- IMAGE UPLOAD VALIDATION ---------- */

    document.querySelectorAll('input[type="file"]').forEach(function (input) {
        input.addEventListener("change", function () {
            const files = Array.from(input.files || []);
            const maxSize = 5 * 1024 * 1024;
            const allowedTypes = [
                "image/jpeg",
                "image/png",
                "image/webp"
            ];

            for (const file of files) {
                if (!allowedTypes.includes(file.type)) {
                    alert("Please select a JPG, PNG, or WebP image.");
                    input.value = "";
                    return;
                }

                if (file.size > maxSize) {
                    alert("The image must not be larger than 5 MB.");
                    input.value = "";
                    return;
                }
            }
        });
    });

    /* ---------- SET DEFAULT DATE ---------- */

    document.querySelectorAll('input[type="date"][data-default-today]').forEach(
        function (dateInput) {
            if (!dateInput.value) {
                const now = new Date();
                const localDate = new Date(
                    now.getTime() - now.getTimezoneOffset() * 60000
                )
                    .toISOString()
                    .slice(0, 10);

                dateInput.value = localDate;
            }
        }
    );

    /* ---------- CONFIRM STATUS CHANGES ---------- */

    document.querySelectorAll("[data-confirm]").forEach(function (element) {
        element.addEventListener("click", function (event) {
            const message =
                element.getAttribute("data-confirm") ||
                "Are you sure you want to continue?";

            if (!window.confirm(message)) {
                event.preventDefault();
            }
        });
    });

    /* ---------- CURRENT YEAR ---------- */

    document.querySelectorAll("[data-current-year]").forEach(function (element) {
        element.textContent = new Date().getFullYear();
    });
});
