document.addEventListener('DOMContentLoaded', function() {
    fetch('data/operations.csv')
        .then(response => response.text())
        .then(data => {
            const rows = data.split('\n').slice(1); // Remove the header row
            const labels = [];
            const values = [];

            rows.forEach(row => {
                const cols = row.split(',');
                labels.push(cols[0]); // Assuming the first column is the label
                values.push(parseFloat(cols[1])); // Assuming the second column is the value
            });

            const ctx = document.getElementById('myChart').getContext('2d');
            const myChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Opérations',
                        data: values,
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        });
});
