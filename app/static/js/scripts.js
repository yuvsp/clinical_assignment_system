/**
 * Renders relevant/irrelevant instructors content into tooltipElement from API-shaped data.
 * Used both for cache (sync) and for fetch response (async).
 */
function renderRelevantContent(data, studentId, day, tooltipElement) {
    tooltipElement.innerHTML = '';
    tooltipElement.dir = 'rtl';

    var strong = document.createElement('strong');
    strong.textContent = 'שיבוצים רלוונטיים:';
    tooltipElement.appendChild(strong);
    tooltipElement.appendChild(document.createElement('br'));

    var relevantForDay = (data.relevant_instructors || []).filter(function (instructor) { return instructor.day === day; });
    relevantForDay.forEach(function (instructor) {
        var form = document.createElement('form');
        form.method = 'post';
        form.action = '/assign_direct';
        form.style.marginBottom = '4px';

        var inputStudent = document.createElement('input');
        inputStudent.type = 'hidden';
        inputStudent.name = 'student_id';
        inputStudent.value = String(studentId);
        form.appendChild(inputStudent);

        var inputInstructor = document.createElement('input');
        inputInstructor.type = 'hidden';
        inputInstructor.name = 'instructor_id';
        inputInstructor.value = String(instructor.id);
        form.appendChild(inputInstructor);

        var inputDay = document.createElement('input');
        inputDay.type = 'hidden';
        inputDay.name = 'assigned_day';
        inputDay.value = day;
        form.appendChild(inputDay);

        var btn = document.createElement('button');
        btn.type = 'submit';
        btn.className = 'btn btn-link btn-assign-suggestion green-background p-1 text-start w-100';
        btn.textContent = instructor.name + ' – ' + instructor.area_of_expertise;
        form.appendChild(btn);

        tooltipElement.appendChild(form);
    });

    var strong2 = document.createElement('strong');
    strong2.textContent = 'לא רלוונטי:';
    strong2.style.display = 'block';
    strong2.style.marginTop = '8px';
    tooltipElement.appendChild(strong2);
    tooltipElement.appendChild(document.createElement('br'));

    var irrelevantForDay = (data.irrelevant_instructors || []).filter(function (instructor) { return instructor.day === day; });
    irrelevantForDay.forEach(function (instructor) {
        var p = document.createElement('p');
        p.className = 'small mb-1';
        if (instructor.reason === 'הקלינאית תפוסה ביום זה') {
            p.style.textDecoration = 'line-through';
            p.classList.add('red-background');
        }
        if (instructor.reason === 'תחום לא מועדף של הסטודנטית') {
            p.classList.add('yellow-background');
        }
        p.textContent = instructor.name + ' – ' + instructor.area_of_expertise + ' (' + (instructor.reason || '') + ')';
        tooltipElement.appendChild(p);
    });

    if (relevantForDay.length === 0 && irrelevantForDay.length === 0) {
        var msg = document.createElement('p');
        msg.className = 'small text-muted mb-0';
        msg.textContent = 'אין מדריכים רלוונטיים ליום זה';
        tooltipElement.appendChild(msg);
    }
}

/**
 * Renders suggestions from the page-load bulk cache (instant, no network).
 */
function renderRelevantFromCache(studentId, day, tooltipElement) {
    var data = (typeof window !== 'undefined' && window.__relevantInstructorsBulk) ? window.__relevantInstructorsBulk[studentId] : null;
    if (data) {
        renderRelevantContent(data, studentId, day, tooltipElement);
    } else {
        fetchInstructors(studentId, day, tooltipElement);
    }
}

/**
 * Fetches suggestions from the API and renders into the popover (fallback when not in cache).
 */
function fetchInstructors(studentId, day, tooltipElement) {
    fetch('/relevant_instructors/' + studentId + '?day=' + encodeURIComponent(day))
        .then(function (response) { return response.json(); })
        .then(function (data) {
            renderRelevantContent(data, studentId, day, tooltipElement);
        })
        .catch(function (error) {
            console.error('Error fetching instructors:', error);
            tooltipElement.innerHTML = '<p class="small text-danger mb-0">שגיאה בטעינה</p>';
        });
}
