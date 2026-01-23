function fetchInstructors(studentId, day, tooltipElement) {
    fetch(`/relevant_instructors/${studentId}?day=${day}`)
        .then(response => response.json())
        .then(data => {
            // Clear the tooltip content
            tooltipElement.innerHTML = '<strong>שיבוצים רלוונטיים:</strong><br>';

            // Add relevant instructors for the specific day
            data.relevant_instructors.forEach(instructor => {
                if (instructor.day === day) {
                    let p = document.createElement('p');
                    p.classList.add('green-background');
                    p.textContent = `${instructor.name} - ${instructor.area_of_expertise}`;
                    tooltipElement.appendChild(p);
                }
            });

            tooltipElement.innerHTML += '<strong>לא רלוונטי:</strong><br>';

            // Add irrelevant instructors for the specific day
            data.irrelevant_instructors.forEach(instructor => {
                if (instructor.day === day) {
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

/* -----------------------------
   Drag & Drop for assignments
------------------------------*/
function showDndAlert(message, level = 'info') {
    const container = document.getElementById('dnd-alert-container');
    if (!container) return;

    const alert = document.createElement('div');
    alert.className = `alert alert-${level} text-right`;
    alert.setAttribute('role', 'alert');
    alert.textContent = message;

    container.innerHTML = '';
    container.appendChild(alert);

    setTimeout(() => {
        if (container.contains(alert)) {
            container.innerHTML = '';
        }
    }, 3500);
}

function initAssignmentDragAndDrop() {
    const assignmentCards = document.querySelectorAll('.assignment-card[draggable="true"]');
    const studentRows = document.querySelectorAll('tr.student-row[data-student-id]');
    const trash = document.getElementById('trash-dropzone');

    if (!assignmentCards.length) return;

    assignmentCards.forEach(card => {
        card.addEventListener('dragstart', (e) => {
            const payload = {
                assignment_id: card.dataset.assignmentId,
                from_student_id: card.dataset.fromStudentId,
                day: card.dataset.day
            };
            e.dataTransfer.setData('application/json', JSON.stringify(payload));
            e.dataTransfer.effectAllowed = 'move';
        });
    });

    studentRows.forEach(row => {
        row.addEventListener('dragover', (e) => {
            e.preventDefault();
            row.classList.add('drag-over');
            e.dataTransfer.dropEffect = 'move';
        });

        row.addEventListener('dragleave', () => {
            row.classList.remove('drag-over');
        });

        row.addEventListener('drop', async (e) => {
            e.preventDefault();
            row.classList.remove('drag-over');

            let payload;
            try {
                payload = JSON.parse(e.dataTransfer.getData('application/json'));
            } catch (err) {
                return;
            }

            const toStudentId = row.dataset.studentId;
            const assignmentId = payload.assignment_id;
            const day = payload.day;

            // If dropping onto the same student -> do nothing
            if (String(payload.from_student_id) === String(toStudentId)) {
                return;
            }

            // Client-side quick check: target already has assignment in that day
            const targetCell = row.querySelector(`td[data-day="${day}"]`);
            if (targetCell && targetCell.querySelector('.assignment-card')) {
                showDndAlert('לסטודנטית כבר יש שיבוץ ביום זה', 'warning');
                return;
            }

            try {
                const res = await fetch(`/api/assignments/${assignmentId}/reassign`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ to_student_id: toStudentId })
                });

                const data = await res.json();

                if (!res.ok || !data.success) {
                    showDndAlert(data.reason || 'לא ניתן להעביר את השיבוץ', 'warning');
                    return;
                }
                showDndAlert('השיבוץ הועבר בהצלחה', 'success');
                // Reload to ensure the table (buttons/tooltips/counts) is consistent with server logic
                setTimeout(() => window.location.reload(), 250);

            } catch (err) {
                console.error(err);
                showDndAlert('שגיאת תקשורת בעת העברת השיבוץ', 'danger');
            }
        });
    });

    if (trash) {
        trash.addEventListener('dragover', (e) => {
            e.preventDefault();
            trash.classList.add('drag-over');
            e.dataTransfer.dropEffect = 'move';
        });

        trash.addEventListener('dragleave', () => {
            trash.classList.remove('drag-over');
        });

        trash.addEventListener('drop', async (e) => {
            e.preventDefault();
            trash.classList.remove('drag-over');

            let payload;
            try {
                payload = JSON.parse(e.dataTransfer.getData('application/json'));
            } catch (err) {
                return;
            }

            const assignmentId = payload.assignment_id;

            try {
                const res = await fetch(`/api/assignments/${assignmentId}`, { method: 'DELETE' });
                const data = await res.json();

                if (!res.ok || !data.success) {
                    showDndAlert(data.reason || 'לא ניתן לבטל את השיבוץ', 'warning');
                    return;
                }

                const card = document.querySelector(`.assignment-card[data-assignment-id="${assignmentId}"]`);
                if (card) {
                    const cell = card.closest('td');
                    if (cell) cell.innerHTML = '';
                }

                showDndAlert('השיבוץ בוטל', 'success');
                setTimeout(() => window.location.reload(), 250);
            } catch (err) {
                console.error(err);
                showDndAlert('שגיאת תקשורת בעת ביטול השיבוץ', 'danger');
            }
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initAssignmentDragAndDrop();
});
