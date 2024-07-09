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
                if (instructor.reason === "Instructor is booked for the selected day") {
                    p.classList.add('red-background');
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


document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.student').forEach(function(element) {
        element.addEventListener('mouseover', function() {
            const studentId = this.getAttribute('data-student-id');
            const tooltipElement = this.querySelector('.instructors-tooltip');
            fetchInstructors(studentId, tooltipElement);
        });
    });
});
