// Market Visualization using D3.js
window.MarketVisualization = {
    svg: null,
    width: 0,
    height: 0,
    root: null,

    render(data) {
        // Clear previous visualization
        d3.select('#tree-visualization').html('');

        // Set dimensions
        const container = document.getElementById('tree-visualization');
        this.width = container.clientWidth;
        
        // Calculate height based on number of nodes to prevent overlap
        const nodeCount = this.countNodes(data);
        const minHeightPerNode = 60; // Minimum vertical space per node
        const calculatedHeight = Math.max(800, nodeCount * minHeightPerNode);
        this.height = Math.min(calculatedHeight, 5000); // Cap at 5000px

        // Create SVG
        this.svg = d3.select('#tree-visualization')
            .append('svg')
            .attr('width', this.width)
            .attr('height', this.height);

        // Create tree layout with increased vertical spacing
        const treeLayout = d3.tree()
            .size([this.height - 100, this.width - 200])
            .separation((a, b) => {
                // Increase vertical separation between nodes
                return a.parent === b.parent ? 2 : 3;
            });

        // Create hierarchy
        this.root = d3.hierarchy(data);
        
        // Calculate tree layout
        treeLayout(this.root);

        // Create group for zoom/pan
        const g = this.svg.append('g')
            .attr('transform', 'translate(100, 50)');

        // Add zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.5, 3])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });

        this.svg.call(zoom);

        // Draw links
        g.selectAll('.link')
            .data(this.root.links())
            .enter()
            .append('path')
            .attr('class', 'link')
            .attr('d', d3.linkHorizontal()
                .x(d => d.y)
                .y(d => d.x))
            .style('fill', 'none')
            .style('stroke', '#ccc')
            .style('stroke-width', 2);

        // Draw nodes
        const nodes = g.selectAll('.node')
            .data(this.root.descendants())
            .enter()
            .append('g')
            .attr('class', d => `node level-${d.data.level} status-${d.data.status}`)
            .attr('transform', d => `translate(${d.y}, ${d.x})`)
            .on('click', (event, d) => this.showNodeDetails(d.data));

        // Add circles
        nodes.append('circle')
            .attr('r', d => {
                // Size based on value
                const baseSize = 8;
                const maxSize = 30;
                if (!this.root.data.value) return baseSize;
                const scale = d.data.value / this.root.data.value;
                return baseSize + (maxSize - baseSize) * scale;
            })
            .style('fill', d => this.getNodeColor(d.data))
            .style('stroke', '#333')
            .style('stroke-width', 2)
            .style('cursor', 'pointer');

        // Add labels
        nodes.append('text')
            .attr('dy', -15)
            .attr('text-anchor', 'middle')
            .style('font-size', '12px')
            .style('font-weight', 'bold')
            .style('fill', '#333')
            .text(d => d.data.name);

        // Add value labels
        nodes.append('text')
            .attr('dy', 25)
            .attr('text-anchor', 'middle')
            .style('font-size', '10px')
            .style('fill', '#666')
            .text(d => {
                if (d.data.value) {
                    return this.formatCurrency(d.data.value);
                }
                return '';
            });

        // Add legend
        this.addLegend();
    },

    getNodeColor(node) {
        const colors = {
            'pending': '#fbbf24',
            'analyzing': '#3b82f6',
            'completed': '#10b981',
            'failed': '#ef4444'
        };
        return colors[node.status] || '#9ca3af';
    },

    addLegend() {
        const legend = this.svg.append('g')
            .attr('class', 'legend')
            .attr('transform', `translate(${this.width - 150}, 20)`);

        const statuses = [
            { status: 'completed', label: 'Completed' },
            { status: 'analyzing', label: 'Analyzing' },
            { status: 'pending', label: 'Pending' },
            { status: 'failed', label: 'Failed' }
        ];

        statuses.forEach((item, i) => {
            const g = legend.append('g')
                .attr('transform', `translate(0, ${i * 25})`);

            g.append('circle')
                .attr('r', 6)
                .style('fill', this.getNodeColor({ status: item.status }));

            g.append('text')
                .attr('x', 15)
                .attr('y', 5)
                .style('font-size', '12px')
                .text(item.label);
        });
    },

    showNodeDetails(node) {
        const detailsContent = document.getElementById('details-content');
        
        let html = `
            <div class="node-details">
                <h4>${node.name}</h4>
                <div class="detail-row">
                    <span class="detail-label">Level:</span>
                    <span class="detail-value">${node.level}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Status:</span>
                    <span class="detail-value status-${node.status}">${node.status}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Value Added:</span>
                    <span class="detail-value">${this.formatCurrency(node.value)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Employment:</span>
                    <span class="detail-value">${this.formatNumber(node.employment)}</span>
                </div>
        `;

        if (node.data && node.data.rationale) {
            html += `
                <div class="detail-row">
                    <span class="detail-label">Rationale:</span>
                    <span class="detail-value">${node.data.rationale}</span>
                </div>
            `;
        }

        if (node.data && node.data.sub_markets && node.data.sub_markets.length > 0) {
            html += `
                <div class="detail-section">
                    <h5>Sub-markets (${node.data.sub_markets.length})</h5>
                    <ul class="submarkets-list">
            `;
            
            node.data.sub_markets.forEach(sm => {
                html += `
                    <li>
                        <strong>${sm.name}</strong><br>
                        Value: ${this.formatCurrency(sm.value_added_usd)}<br>
                        Employment: ${this.formatNumber(sm.employment_count)}
                    </li>
                `;
            });
            
            html += `
                    </ul>
                </div>
            `;
        }

        html += `</div>`;
        
        detailsContent.innerHTML = html;
    },

    formatCurrency(value) {
        if (!value) return '$0';
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(value);
    },

    formatNumber(value) {
        if (!value) return '0';
        return new Intl.NumberFormat('en-US').format(value);
    },

    countNodes(node) {
        // Recursively count all nodes in the tree
        let count = 1;
        if (node.children && node.children.length > 0) {
            node.children.forEach(child => {
                count += this.countNodes(child);
            });
        }
        return count;
    }
};
