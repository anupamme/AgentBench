function getAge(user) {
  return user.profile.age;
}

function getName(user) {
  return user.name || 'Anonymous';
}

module.exports = { getAge, getName };
