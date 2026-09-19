(function () {
  "use strict";

  // The copied text is read straight out of the block on screen, so what lands
  // on the clipboard is always what the reader can see.
  function blockText(block) {
    var code = block.querySelector("pre code");
    return code ? code.textContent : "";
  }

  function reset(button) {
    button.textContent = "Copy";
    button.className = "copy";
  }

  function report(button, label, state, path) {
    button.textContent = label;
    button.className = "copy " + state;
    button.setAttribute("data-copy-path", path);
    window.setTimeout(function () {
      reset(button);
    }, 3000);
  }

  // Used when the clipboard API is missing or refused, for example on an
  // insecure origin.
  function copyViaTextarea(text) {
    var area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.top = "-1000px";
    document.body.appendChild(area);
    area.select();
    area.setSelectionRange(0, text.length);
    var copied = false;
    try {
      copied = document.execCommand("copy");
    } catch (error) {
      copied = false;
    }
    document.body.removeChild(area);
    return copied;
  }

  // Last resort: select the block itself so the reader can copy it by hand.
  function selectBlock(block) {
    var code = block.querySelector("pre code");
    if (!code || !window.getSelection || !document.createRange) {
      return;
    }
    var range = document.createRange();
    range.selectNodeContents(code);
    var selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  }

  function fallback(button, block, text) {
    if (copyViaTextarea(text)) {
      report(button, "Copied", "done", "textarea");
      return;
    }
    selectBlock(block);
    report(button, "Select the text to copy", "failed", "manual");
  }

  function wire(block) {
    var button = block.querySelector(".copy");
    if (!button) {
      return;
    }
    button.addEventListener("click", function () {
      var text = blockText(block);
      button.setAttribute("data-copy-length", String(text.length));
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(text).then(
          function () {
            report(button, "Copied", "done", "clipboard");
          },
          function () {
            fallback(button, block, text);
          }
        );
        return;
      }
      fallback(button, block, text);
    });
  }

  var blocks = document.querySelectorAll(".code");
  for (var i = 0; i < blocks.length; i += 1) {
    wire(blocks[i]);
  }

  // The contents list ships closed so it never pushes the guide off a phone
  // screen. On a wide screen it becomes a sidebar, where open is the useful
  // state.
  var toc = document.getElementById("toc");
  if (toc && window.matchMedia) {
    var wide = window.matchMedia("(min-width: 1000px)");
    var follow = function (query) {
      toc.open = query.matches;
    };
    follow(wide);
    if (wide.addEventListener) {
      wide.addEventListener("change", follow);
    }
    // Tapping an entry on a phone should get out of the way.
    toc.addEventListener("click", function (event) {
      if (event.target.tagName === "A" && !wide.matches) {
        toc.open = false;
      }
    });
  }
})();
