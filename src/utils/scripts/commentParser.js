function isValidUrl(str) {
    try {
        new URL(str);
        return true;
    } catch (_) {
        return false;
    }
}

function parseComment(element) {
    let result = [];

    let contentDiv = element.querySelector('div.content');
    if (!contentDiv) return result;

    contentDiv.childNodes.forEach(n => {
        if (n.nodeType === 3) {
            let txt = n.textContent.trim();
            if (txt !== "") {
                result.push({ type: "text", value: txt });
            }
        }
        else if (n.nodeType === 1) {
            if (n.classList.contains("b")) {
                result.push({
                    type: "b",
                    value: n.textContent.trim()
                });
            }
            else if (n.classList.contains("url")) {
                let href = n.href ? n.href.trim() : "";
                let text = n.textContent.trim();
                if (href.startsWith("http") || text.startsWith("www.") || isValidUrl(href)) {
                    result.push({ type: "url", value: href });
                } else if (text !== "") {
                    result.push({ type: "text", value: text });
                }
            }
            else {
                let skipTags = ["FOOTER", "A", "BUTTON", "SPAN"];
                if (!skipTags.includes(n.tagName)) {
                    let txt = n.textContent.trim();
                    if (txt !== "") {
                        result.push({ type: "text", value: txt });
                    }
                }
            }
        }
    });
    return result;
}

return parseComment(arguments[0]);
