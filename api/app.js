'use strict';

const path = require('node:path');
const AutoLoad = require('@fastify/autoload');
const fastifyCors = require('@fastify/cors');

const options = {};

module.exports = async function (fastify, opts) {
  fastify.register(AutoLoad, {
    dir: path.join(__dirname, 'plugins'),
    options: Object.assign({}, opts),
  });

  fastify.register(AutoLoad, {
    dir: path.join(__dirname, 'routes'),
    options: Object.assign({}, opts),
  });

  await fastify.register(fastifyCors, {
    origin: true, // or specify allowed origins
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  });
};

module.exports.options = options;
