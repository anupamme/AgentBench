function getAge(user) {
  return user.profile?.age ?? null;
}

function getName(user) {
  return user.name || 'Anonymous';
}

module.exports = { getAge, getName };
