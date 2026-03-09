function isValidUrl(str) {
    try {
        new URL(str);
        return true;
    } catch (_) {
        return false;
    }
}

function cleanText(text) {
    text = text.replace(/https?:\/\/\S+/g, '');
    text = text.replace(/www\.\S+/g, '');
    text = text.replace(/---\s*spoiler\s*---/gi, '');
    text = text.replace(/son güncelleme:\s*\d{2}\.\d{2}\.\d{4}\s*\d{2}\.\d{2}/gi, '');
    text = text.replace(/[:\-=*_.]{3,}/g, '');
    text = text.replace(/%\d+/g, '');
    text = text.replace(/\s+/g, ' ').trim();

    return text;
}

function parseComment(element) {
    let result = [];

    let contentDiv = element.querySelector('div.content');
    if (!contentDiv) return result;

    contentDiv.childNodes.forEach(n => {
        if (n.nodeType === 3) {
            let txt = cleanText(n.textContent);
            if (txt !== "") {
                result.push({ type: "text", value: txt });
            }
        }
        else if (n.nodeType === 1) {
            if (n.classList.contains("b")) {
                let txt = cleanText(n.textContent);
                if (txt !== "") {
                    result.push({ type: "b", value: txt });
                }
            }
            else if (n.classList.contains("url")) {
                return;
            }
            else {
                let skipTags = ["FOOTER", "A", "BUTTON", "SPAN"];
                if (!skipTags.includes(n.tagName)) {
                    let txt = cleanText(n.textContent);
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
