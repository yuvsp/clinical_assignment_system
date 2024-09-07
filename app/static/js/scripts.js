function fetchInstructors(studentId, day, tooltipElement) {
    fetch(`/relevant_instructors/${studentId}?day=${day}`)
        .then(response => response.json())
        .then(data => {
            // Clear the tooltip content
            tooltipElement.innerHTML = '<strong>שיבוצים רלוונטיים:</strong><br>';  // Add <br> after title
            
            // Add relevant instructors for the specific day
            data.relevant_instructors.forEach(instructor => {
                if (instructor.day === day) {  // Filter by day
                    let p = document.createElement('p');
                    p.classList.add('green-background');
                    p.textContent = `${instructor.name} - ${instructor.area_of_expertise}`;
                    tooltipElement.appendChild(p);
                }
            });

            tooltipElement.innerHTML += '<strong>לא רלוונטי:</strong><br>';  // Add <br> after title
            
            // Add irrelevant instructors for the specific day
            data.irrelevant_instructors.forEach(instructor => {
                if (instructor.day === day) {  // Filter by day
                    let p = document.createElement('p');
                    
                    if (instructor.reason === "הקלינאית תפוסה ביום זה") {
                        p.style.textDecoration = 'line-through';
                        p.classList.add('red-background');
                    }
                    if (instructor.reason === "תחום לא מועדף של הסטודנטית") {
                        p.classList.add('yellow-background');
                    }
                    p.textContent = `${instructor.name} - ${instructor.area_of_expertise} (${instructor.reason})`;
                    tooltipElement.appendChild(p);
                }
            });

            // Handle case when no instructors are available
            if (!tooltipElement.innerHTML.includes('p')) {
                tooltipElement.innerHTML += '<p>אין מדריכים רלוונטיים ליום זה</p>';
            }
        })
        .catch(error => {
            console.error('Error fetching instructors:', error);
        });
}
