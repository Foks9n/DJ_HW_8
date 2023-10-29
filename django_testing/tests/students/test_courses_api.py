import pytest
from django.conf import settings
from django.contrib.auth.models import User
from model_bakery import baker
from rest_framework.test import APIClient

from students.models import Course, Student


@pytest.fixture
def admin():
    return User.objects.create_user(username='admin')


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def course_factory():
    def factory(*args, **kwargs):
        return baker.make(Course, make_m2m=True, *args, **kwargs)
    
    return factory


@pytest.fixture
def students_factory():
    def factory(*args, **kwargs):
        return baker.make(Student, *args, **kwargs)
    
    return factory


@pytest.fixture
def max_students():
    return settings.MAX_STUDENTS_PER_COURSE


@pytest.mark.django_db
def test_get_course(client, course_factory, students_factory):
    students = students_factory(_quantity=4)
    course = course_factory(_quantity=1, students=students)
    course_id = course[0].id
    response = client.get(f'/api/v1/courses/{course_id}/')
    data = response.json()
    students_m2m_ids = [student.id for student in course[0].students.all()]

    assert response.status_code == 200
    assert course[0].id == data['id']
    assert course[0].name == data['name']
    assert students_m2m_ids == data['students']


@pytest.mark.django_db
def test_get_courses(client, course_factory, students_factory):
    students = students_factory(_quantity=6)
    courses = course_factory(_quantity=10, students=students)
    response = client.get('/api/v1/courses/')
    data = response.json()
    students_m2m_ids = [student.id for student in courses[0].students.all()]

    assert response.status_code == 200
    assert len(data) == 10

    for i in range(len(data)):
        assert data[i]['id'] == courses[i].id
        assert data[i]['name'] == courses[i].name
        assert data[i]['students'] == students_m2m_ids


@pytest.mark.django_db
def test_filter_by_course_id(client, course_factory, students_factory):
    students = students_factory(_quantity=4)
    courses = course_factory(_quantity=15, students=students)
    students_m2m_ids = [student.id for student in courses[0].students.all()]
    course_id = courses[3].id
    course_obj = Course.objects.get(id=course_id)
    response = client.get('/api/v1/courses/', {'id': course_id})
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]['id'] == int(course_id)
    assert data[0]['name'] == course_obj.name
    assert data[0]['students'] == students_m2m_ids


@pytest.mark.django_db
def test_filter_by_course_name(client, course_factory, students_factory):
    students = students_factory(_quantity=5)
    courses = course_factory(_quantity=25, students=students)
    students_m2m_ids = [student.id for student in courses[0].students.all()]
    course_name = courses[9].name
    course_obj = Course.objects.get(name=course_name)
    response = client.get('/api/v1/courses/', {'name': course_name})
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]['id'] == course_obj.id
    assert data[0]['name'] == course_obj.name
    assert data[0]['students'] == students_m2m_ids


@pytest.mark.django_db
def test_create_course(client):
    course_json = {
        'name': 'Some course',
    }

    response = client.post('/api/v1/courses/', data=course_json, format='json')
    course_id = response.data.get('id')
    response_after_creating = client.get(f'/api/v1/courses/{course_id}/')

    assert response.status_code == 201
    assert response.data['name'] == 'Some course'
    assert response_after_creating.status_code == 200
    assert response_after_creating.data['name'] == 'Some course'


@pytest.mark.django_db
def test_update_course(client, course_factory):
    course = course_factory()
    course_id = course.id

    update_json = {
        'name': 'Update course name'
    }

    response = client.put(f'/api/v1/courses/{course_id}/', data=update_json, format='json')

    assert response.status_code == 200
    assert response.data['id'] == course_id
    assert response.data['name'] == 'Update course name'


@pytest.mark.django_db
def test_delete_course(client, course_factory):
    course = course_factory()
    course_id = course.id
    response_before_delete = client.get(f'/api/v1/courses/{course_id}/')
    response = client.delete(f'/api/v1/courses/{course_id}/')
    response_after_delete = client.get(f'/api/v1/courses/{course_id}/')

    assert response_before_delete.status_code == 200
    assert response.status_code == 204
    assert response.data == None
    assert response_after_delete.status_code == 404


@pytest.mark.parametrize('max_count', [0, 4, 8, 19, 20, 12])
def test_valid_max_students_per_course(max_students, max_count):
    assert max_students >= max_count, 'Количество студентов на курсе должно быть меньше или равно 20'


@pytest.mark.parametrize('max_count', [22, 121, 21, 34, 56])
def test_invalid_max_students_per_course(max_students, max_count):
    assert max_students < max_count, 'Количество студентов на курсе должно быть меньше или равно 20'