'use strict';

const fp = require('fastify-plugin');
const jwksRsa = require('jwks-rsa');
const fastifyJwt = require('@fastify/jwt');
const config = require('../config');

module.exports = fp(async function (fastify) {
  const jwks = jwksRsa({
    jwksUri: `${config.keycloakUrl}/realms/${config.keycloakRealm}/protocol/openid-connect/certs`,
  });

  await fastify.register(fastifyJwt, {
    decode: { complete: true },
    secret: async (request, token) => {
      const kid = token.header.kid;
      const key = await jwks.getSigningKey(kid);
      return key.getPublicKey();
    },
    sign: { algorithm: 'RS256' },
  });

  fastify.decorate('authenticate', async function (request, reply) {
    try {
      await request.jwtVerify();
      const roles = request.user?.realm_access?.roles || [];
      if (!roles.includes('prothetic_user')) {
        return reply.code(403).send({ error: 'Forbidden' });
      }
    } catch (err) {
      return reply.code(401).send({ error: 'Unauthorized' });
    }
  });
});
