function getNetBoxTheme() {
  // Try a few known keys/values and fall back to light
  const candidates = [
    localStorage.getItem("color-mode"),
    localStorage.getItem("theme"),
    document.documentElement.getAttribute("data-bs-theme"),
  ].filter(Boolean);

  const value = (candidates[0] || "").toLowerCase();
  if (value === "dark" || value === "light") return value;

  // Some setups store "system"
  if (value === "system") {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }

  return "light";
}

function drawTopology(data, svgElementId) {
    const edges = data.edges;
    const items = data.items;
    const width = data.width;
    const theme = getNetBoxTheme();
    const assets = window.NBFORTIGATE_ASSETS || {};
    const themeColor = {
        'light': {
            'line': 'green',
            'text': 'black',
            'node': '/static/netbox_fortigate/img/dark-fortigate.png',
            'host': '/static/netbox_fortigate/img/host.png',
        },
        'dark': {
            'line': '#00FF00',
            'text': 'white',
            'node': '/static/netbox_fortigate/img/light-fortigate.png',
            'host': '/static/netbox_fortigate/img/host.png',
        }
    }

    const svg = document.getElementById('topology');
    svg.setAttribute('width', width + 1);
    svg.innerHTML = ''; // Clear previous contents if any


    edges.forEach(link => {
        // Draw line
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        //line.setAttribute('id', 'line-' + link.id);
        line.setAttribute('x1', link.x1);
        line.setAttribute('y1', link.y1 + 15);
        line.setAttribute('x2', link.x2);
        line.setAttribute('y2', link.y2 + 15);
        line.setAttribute('stroke', themeColor[theme]['line']);
        line.setAttribute('stroke-width', '1.5');
        svg.appendChild(line);

        // Draw label1
        const text1 = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text1.setAttribute('class', 'label1');
        text1.setAttribute('x', link.label1_x);
        text1.setAttribute('y', link.label_y + 15);
        text1.setAttribute('fill', themeColor[theme]['text']);
        text1.textContent = link.label1;
        svg.appendChild(text1);

        // Draw label2
        const text2 = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        text2.setAttribute('class', 'label2');
        text2.setAttribute('x', link.label2_x);
        text2.setAttribute('y', link.label_y + 15);
        text2.setAttribute('fill', themeColor[theme]['text']);
        text2.textContent = link.label2;
        svg.appendChild(text2);
    });

    // Draw nodes
    const ICON_SIZE = 45;
    items.forEach(node => {
        const image = document.createElementNS('http://www.w3.org/2000/svg', 'image');
        image.setAttribute('href', themeColor[theme][node.type]); // Use `xlink:href` if older browsers support is needed
        image.setAttribute('width', ICON_SIZE);
        image.setAttribute('height', ICON_SIZE);
        image.setAttribute('x', node.x);  // Adjust the position based on icon size
        image.setAttribute('y', node.y + 15);  // Adjust the position based on icon size
        if (node.type == 'node') {
            image.setAttribute('class', node.class);
            const titleElement = document.createElementNS('http://www.w3.org/2000/svg', 'title');
            titleElement.textContent = 'Policy ID: ' + node.policy_id;
            if (node.status === 'unknown') {
                titleElement.textContent = 'Unable to pull policy from the device';
            }
            image.appendChild(titleElement);
        } else {
            image.setAttribute('class', node.class + ' ' + theme);
        }
        svg.appendChild(image);

        // Add the circled check or circled X above the node
        if (node.type == 'node') {
            const symbolElement = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            var symbol = node.status === 'allow' ? '✓' : '✗'; // Check or X based on status
            if (node.status === 'unknown') {
                symbol = '?';
            }
            symbolElement.textContent = symbol;
            symbolElement.setAttribute('x', node.x + 24);
            symbolElement.setAttribute('y', node.y + 20);  // Above the node
            symbolElement.setAttribute('fill', node.status === 'allow' ? 'green' : 'red');
            symbolElement.classList.add('node-symbol', node.status); // Add classes for styling
            svg.appendChild(symbolElement);
        }

        if (node.role == 'src_host') {
            const srcLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            srcLabel.setAttribute('class', 'host_label' );
            srcLabel.setAttribute('x', node.x + 22);
            srcLabel.setAttribute('y', node.y + 12);  // Above the node
            srcLabel.setAttribute('fill', themeColor[theme]['text']);
            srcLabel.textContent = 'Source';
            svg.appendChild(srcLabel);
        }

        const nodeName = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        nodeName.setAttribute('class', node.class);
        nodeName.setAttribute('x', node.x + 22);
        nodeName.setAttribute('y', node.y + 75);  // Below the node
        nodeName.textContent = node.name;
        nodeName.setAttribute('fill', themeColor[theme]['text']);
        svg.appendChild(nodeName);

        // IP address of the nodes
        if (node.ip) {
            const ip = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            ip.setAttribute('class', 'host_label');
            ip.setAttribute('x', node.x + 22);
            ip.setAttribute('y', node.y + 90);  // Above the node
            ip.setAttribute('fill', themeColor[theme]['text']);
            ip.textContent = '(' + node.ip + ')';
            svg.appendChild(ip);
        }

        if (node.role == 'dst_host') {
            const dstLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            dstLabel.setAttribute('class', 'host_label');
            dstLabel.setAttribute('x', node.x + 22);
            dstLabel.setAttribute('y', node.y + 12);  // Above the node
            dstLabel.setAttribute('fill', themeColor[theme]['text']);
            dstLabel.textContent = 'Destination';
            svg.appendChild(dstLabel);
        }

        if (node.policy_id !== 0 && node.type == 'node') {
            image.addEventListener('click', function() {
                // Open the URL in a new tab
                window.open(`${node.fortigate_id}/${node.policy_id}`, '_blank');
                //showModalWithUrl(`${node.fortigate_id}/${node.policy_id}`);  // Your Django view
            });
            

        }
    });
}


document.body.addEventListener("htmx:afterRequest", (event) => {
  if (!event.detail.elt || event.detail.elt.id !== "form1") return;

  const xhr = event.detail.xhr;

  let data;
  try {
    data = JSON.parse(xhr.responseText || "{}");
  } catch (e) {
    // NetBox toast area exists; if you don’t have showToast yet, use alert temporarily
    alert("Server returned invalid JSON.");
    return;
  }

  if (xhr.status >= 400 || data.status !== "Success") {
    alert(data.message || "Request failed.");
    return;
  }

  drawTopology(data, "topology");
});


function showModalWithUrl(url) {
    const modal = document.getElementById('modal');
    const modalBody = document.getElementById('modal-body');
    const closeModal = document.getElementById('modal-close');
  
    // Show the modal
    modal.style.display = 'block';
  
    // Load content from the URL (can be a Django view that returns HTML)
    fetch(url)
      .then(response => response.text())
      .then(html => {
        modalBody.innerHTML = html;
      })
      .catch(err => {
        modalBody.innerHTML = '<p>Error loading content</p>';
      });
  
    // Close the modal when clicking the close button
    closeModal.onclick = function () {
      modal.style.display = 'none';
      modalBody.innerHTML = ''; // optional: clear content
    };
  
    // Also close modal if clicking outside the modal content
    window.onclick = function (event) {
      if (event.target === modal) {
        modal.style.display = 'none';
        modalBody.innerHTML = '';
      }
    };
  }
  
