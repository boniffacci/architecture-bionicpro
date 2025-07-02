'use strict';

module.exports = async function (fastify, opts) {
  fastify.get('/reports', { preHandler: fastify.authenticate }, async function (request, reply) {
    return {
      reports: Array.from({ length: 5 }, (_, i) => ({
        id: i + 1,
        date: new Date(2024, 0, 15 - i).toISOString().split('T')[0],
        product: [
          'Миодатчик',
          'Чип типа ESP32',
          'Актуатор',
          'Батарея',
          'Корпус',
          'Система управления батареей',
        ][Math.floor(Math.random() * 5)],
        quantity: Math.floor(Math.random() * 81) + 20,
        quality_score: Math.floor(Math.random() * 4) + 97,
        defects: Math.floor(Math.random() * 3),
        batch_number: `BP-${String(i + 1).padStart(3, '0')}-24`,
      })),
    };
  });
};
