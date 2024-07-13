function fetchInstructors(studentId, tooltipElement) {
    fetch(`/relevant_instructors/${studentId}`)
        .then(response => response.json())
        .then(data => {
            tooltipElement.innerHTML = '<strong>Relevant Instructors:</strong>';
            data.relevant_instructors.forEach(instructor => {
                let p = document.createElement('p');
                p.classList.add('green-background');
                p.textContent = `${instructor.name} - ${instructor.area_of_expertise} - ${instructor.day}`;
                tooltipElement.appendChild(p);
            });
            tooltipElement.innerHTML += '<strong>Irrelevant Instructors:</strong>';
            data.irrelevant_instructors.forEach(instructor => {
                let p = document.createElement('p');
                p.style.textDecoration = 'line-through';
                if (instructor.reason === "הקלינאית תפוסה ביום זה") {
                    p.classList.add('red-background');
                }
                if (instructor.reason === "תחום לא מועדף של הסטודנטית") {
                    p.classList.add('yellow-background');
                }
                p.textContent = `${instructor.name} - ${instructor.area_of_expertise} - ${instructor.day} (${instructor.reason})`;
                tooltipElement.appendChild(p);
            });
        })
        .catch(error => {
            console.error('Error fetching instructors:', error);
        });
}

document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.student').forEach(function(element) {
        element.addEventListener('mouseover', function() {
            const studentId = this.getAttribute('data-student-id');
            const tooltipElement = this.querySelector('.instructors-tooltip');
            fetchInstructors(studentId, tooltipElement); 
        });
    });
});
